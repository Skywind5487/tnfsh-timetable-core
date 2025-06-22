from __future__ import annotations  
from typing import TYPE_CHECKING, List, Set, Dict, Optional, Literal, Tuple, TypedDict, TypeAlias
import logging
from unittest import result
import aiohttp
from aiohttp import client_exceptions
import asyncio
from bs4 import BeautifulSoup
import re
from pathlib import Path
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)
if TYPE_CHECKING:
    from tnfsh_timetable_core.index.index import Index

from tnfsh_timetable_core.utils.logger import get_logger
from tnfsh_timetable_core.abc.crawler_abc import BaseCrawlerABC
from tnfsh_timetable_core.index.models import ReverseIndexResult, TargetInfo



# 設定日誌
logger = get_logger(logger_level="DEBUG")

from tnfsh_timetable_core.timetable.models import (
    TimetableSchema,
    FetchError,
    CourseInfo,
    CounterPart
)


class TimetableCrawler(BaseCrawlerABC):
    """課表爬蟲實作"""
    
    # 預設別名列表，作為類別屬性
    DEFAULT_ALIASES: List[Set[str]] = [{"朱蒙", "吳銘"}]
    
    def __init__(self, aliases: Optional[List[Set[str]]] = None):
        """
        初始化課表爬蟲

        Args:
            aliases (Optional[List[Set[str]]], optional): 別名列表. 預設為 None
        """
        self.aliases = aliases or self.DEFAULT_ALIASES
        self._url_cache: Dict[str, str] = {}  # 快取不同目標的 URL

    @staticmethod
    def _parse_periods(row: BeautifulSoup) -> Optional[Tuple[str, Tuple[str, str]]]:
        """解析課表時間"""
        cells = row.find_all("td")
        if len(cells) < 2:
            return None
            
        lesson_name = cells[0].text.replace("\n", "").replace("\r", "")
        time_text = cells[1].text.replace("\n", "").replace("\r", "")
        
        re_pattern = r'(\d{2})(\d{2})'
        re_sub = r'\1:\2'
        times = [re.sub(re_pattern, re_sub, t.replace(" ", "")) for t in time_text.split("｜")]
        if len(times) == 2:
            return (lesson_name, (times[0], times[1]))
        return None    
    @staticmethod
    def _parse_cell(class_td: BeautifulSoup) -> Optional[CourseInfo]:
        """分析課程td元素為 CourseInfo 格式"""
        def clean_text(text: str) -> str:
            """清理文字內容，移除多餘空格與換行"""
            return text.strip("\n").strip("\r").strip(" ").replace(" ", ", ")

        def is_teacher_p(p_tag: BeautifulSoup) -> bool:
            """檢查是否為包含教師資訊的p標籤"""
            return bool(p_tag.find_all('a'))
        
        def parse_teachers(teacher_ps: List[BeautifulSoup]) -> Dict[str, str]:
            """解析所有教師p標籤的資訊"""
            teachers_dict = {}
            for p in teacher_ps:
                for link in p.find_all('a'):
                    name = clean_text(link.text)
                    href = link.get('href', '')
                    teachers_dict[name] = href
            return teachers_dict
        
        def combine_class_name(class_ps: List[BeautifulSoup]) -> str:
            """組合課程名稱"""
            texts = [clean_text(p.text) for p in class_ps]
            return ''.join(filter(None, texts)).replace("\n", ", ").replace("\u00a0", "")
        ps = class_td.find_all('p')
        if not ps:
            return None
        
        teacher_ps = []
        class_ps = []
        for p in ps:
            if is_teacher_p(p):
                teacher_ps.append(p)
            else:
                class_ps.append(p)
        
        # 解析教師資訊為 CounterPart 列表
        counterparts = []
        if teacher_ps:
            for p in teacher_ps:
                for link in p.find_all('a'):
                    name = clean_text(link.text)
                    href = link.get('href', '')
                    if name and href:  # 只有當名字和連結都存在時才加入
                        counterparts.append(CounterPart(participant=name, url=href))
        
        # 解析課程名稱
        subject = ""
        if class_ps:
            subject = combine_class_name(class_ps)
        elif not counterparts:  # 如果既沒有課程名稱也沒有教師
            return None
        
        # 返回 CourseInfo 物件
        if subject or counterparts:
            return CourseInfo(
                subject=subject,
                counterpart=counterparts if counterparts else None
            )
        return None
    
    def _resolve_target(self, target: str, index: Index) -> Optional[TargetInfo]:
        """根據目標名稱解析別名"""
        result = index[target]

        if result:
            if isinstance(result, list):
                raise KeyError(f"🔄 {target} 有多個對應的ID: {result}")
            else:
                logger.debug(f"🎯 找到 {target} 的TimeTable網址")
                return result

        for alias_set in self.aliases:
            if target in alias_set:
                candidates = alias_set - {target}
                for alias in candidates:
                    tmp_result = index[alias]
                    if tmp_result:
                        if isinstance(tmp_result, list):
                            raise KeyError(f"🔄 {alias} 有多個對應的ID: {tmp_result}")
                        else:
                            logger.info(f"🔄 將 {target} 解析為別名 {alias}")
                            return tmp_result
                    logger.debug(f"找不到 {alias} 對應的TimeTable網址")
        return None

    async def _get_url(self, target: str, refresh: bool = False) -> str:
        """獲取目標的完整 URL"""
        if not refresh and target in self._url_cache:
            return self._url_cache[target]
        from tnfsh_timetable_core import TNFSHTimetableCore
        core = TNFSHTimetableCore()
        index = await core.fetch_index(refresh=refresh)
        if index.reverse_index is None:
            logger.error("❌ 無法獲取Index資料")
            raise FetchError("無法獲取Index資料")

        logger.debug(f"🔍 解析目標：{target}")
        real_target = self._resolve_target(target, index)
        if real_target is None:
            logger.error(f"❌ 找不到 {target} 的Timetable網址")
            raise FetchError(f"找不到 {target} 的Timetable網址")

        relative_url = real_target.url

        url = index.base_url + relative_url
        self._url_cache[target] = url
        logger.debug(f"🌐 準備請求網址：{url}")
        return url

    @retry(
        retry=retry_if_exception_type((
            client_exceptions.ClientError,
            client_exceptions.ServerTimeoutError,
            asyncio.TimeoutError
        )),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        retry_error_cls=FetchError
    )
    async def fetch_raw(self, target: str, refresh: bool = False, *args, **kwargs) -> BeautifulSoup:
        """
        抓取原始課表 HTML

        Args:
            target (str): 目標名稱（班級或教師）
            refresh (bool, optional): 是否強制更新索引快取. 預設為 False

        Returns:
            BeautifulSoup: 解析後的 HTML 内容

        Raises:
            FetchError: 當發生網路請求錯誤時拋出
        """
        url = await self._get_url(target, refresh=refresh)
        headers = self.get_headers()

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                logger.debug(f"📡 發送請求：{target}")
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    content = await response.read()
                    logger.debug(f"📥 收到回應：{target}")
                    soup = BeautifulSoup(content, 'html.parser')
                    return soup

        except client_exceptions.ClientResponseError as e:
            error_msg = f"HTTP 狀態碼錯誤 {e.status}: {e.message}"
            logger.error(f"❌ {error_msg}")
            raise FetchError(error_msg)

        except client_exceptions.ClientError as e:
            error_msg = f"網路請求錯誤：{str(e)}"
            logger.warning(f"⚠️ {error_msg}")
            raise  # 讓 tenacity 處理重試

        except (client_exceptions.ServerTimeoutError, asyncio.TimeoutError) as e:
            error_msg = "請求超時"
            logger.warning(f"⚠️ {error_msg}")
            raise  # 讓 tenacity 處理重試

        except Exception as e:
            error_msg = f"未預期的錯誤：{str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FetchError(error_msg)

    def parse(self, soup: BeautifulSoup, target: str, target_url: str, *args, **kwargs) -> TimetableSchema:
        """
        解析 BeautifulSoup 物件為結構化資料

        Args:
            soup (BeautifulSoup): HTML 解析樹
            target: 目標名稱（班級或教師）
            target_url: 目標的課表連結

        Returns:
            TimetableSchema: 解析後的結構化資料

        Raises:
            FetchError: 當解析失敗時拋出
        """
        
        try:
            # 擷取更新日期
            update_element = soup.find('p', class_='MsoNormal', align='center')
            if update_element:
                spans = update_element.find_all('span')
                last_update = spans[1].text if len(spans) > 1 else "No update date found."
                logger.debug(f"📅 更新日期：{last_update}")
            else:
                last_update = "No update date found."
                logger.warning("⚠️ 找不到更新日期")

            # 擷取課表 table 並移除 border
            main_table = None
            for table in soup.find_all("table"):
                new_table = BeautifulSoup('<table></table>', 'html.parser').table
                for row in table.find_all("tr"):
                    for td in row.find_all('td'):
                        if td.get('style') and 'border' in td['style']:
                            td.decompose()
                    if len(row.find_all('td')) == 7:
                        new_table.append(row)
                        
                if len(new_table.find_all('tr')) > 0:
                    main_table = new_table
                    break

            if main_table is None:
                logger.error("❌ 找不到符合格式的Timetable")
                raise FetchError("找不到符合格式的Timetable")

            # 擷取 periods
            periods: Dict[str, Tuple[str, str]] = {}
            for row in main_table.find_all("tr"):
                result = self._parse_periods(row)
                if result:
                    lesson_name, times = result
                    periods[lesson_name] = times

            # 擷取 table raw 格式
            from tnfsh_timetable_core.timetable.models import CourseInfo
            table: List[List[CourseInfo | None]] = []
            for row in main_table.find_all("tr"):
                cells = row.find_all("td")[2:]  # 跳過前兩列（節次和時間）
                row_data = []
                for cell in cells:
                    row_data.append(self._parse_cell(cell))
                if row_data:
                    table.append(row_data)
            # 行列互換
            table = list(map(list, zip(*table)))  # 轉置表格

            simple_target_url = str(target_url.split("/")[-1])
            # 直接回傳 TimetableSchema
            return TimetableSchema(
                table=table, 
                periods=periods,
                type="class" if target.isdigit() else "teacher",
                target=target,
                target_url=simple_target_url,
                last_update=last_update
            )
        except Exception as e:
            error_msg = f"解析錯誤：{str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FetchError(error_msg)    
    
    async def fetch(self, target: str, refresh: bool = False, *args, **kwargs) -> TimetableSchema:
        """
        完整的課表抓取流程

        Args:
            target (str): 目標名稱（班級或教師）
            refresh (bool, optional): 是否強制更新索引快取. 預設為 False

        Returns:
            TimetableSchema: 解析後的課表資料

        Raises:
            FetchError: 當抓取或解析失敗時拋出
        """
        raw_html = await self.fetch_raw(target, refresh=refresh)
        target_url = await self._get_url(target, refresh=refresh)
        result = self.parse(raw_html, target=target, target_url=target_url)
        
        logger.info(f"✅ {target}[抓取]完成")
        return result

if __name__ == "__main__":
    # For test cases, see: tests/test_timetable/test_crawler.py
    pass