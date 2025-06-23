from __future__ import annotations  
from operator import index
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
logger = get_logger(logger_level="INFO")

from tnfsh_timetable_core.timetable.models import (
    TimetableSchema,
    FetchError,
    CourseInfo,
    CounterPart
)
from tnfsh_timetable_core.index.index import Index

class TimetableCrawler(BaseCrawlerABC):
    """課表爬蟲實作"""
    
    # 預設別名列表，作為類別屬性
    DEFAULT_ALIASES: List[Set[str]] = [{"朱蒙", "吳銘"}]
    
    def __init__(self, 
                 aliases: Optional[List[Set[str]]] = None,
                 index: Optional[Index] = None
    ):
        """
        初始化課表爬蟲

        Args:
            aliases (Optional[List[Set[str]]], optional): 別名列表. 預設為 None
        """
        self.aliases = aliases or self.DEFAULT_ALIASES
        self._url_cache: Dict[str, str] = {}  # 快取不同目標的 URL
        self._index : Index | None = index  # 用於存儲索引資料

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
            return text.replace("\n", "").replace("\r", "").strip(" ").replace(" ", "")

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
        """根據目標名稱解析並返回 TargetInfo 或 URL"""
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

    async def _resolve_target_info(self, target: str, refresh: bool = False) -> tuple[TargetInfo, str]:
        """
        解析目標名稱並取得 TargetInfo 與完整 URL
        """
        if not self._index:
            # 如果索引不存在，則重新抓取索引
            from tnfsh_timetable_core.index.index import Index
            self._index = await Index.fetch(refresh=refresh)
        index = self._index
        real_target = self._resolve_target(target, index)
        if real_target is None:
            logger.error(f"❌ 找不到 {target} 的Timetable網址")
            raise FetchError(f"找不到 {target} 的Timetable網址")
        relative_url = real_target.url
        url = index.base_url + relative_url
        self._url_cache[target] = url  # 僅快取 url
        logger.debug(f"🌐 準備請求網址：{url}")
        return real_target, url

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
    async def fetch_raw(self, target: str, refresh: bool = False, *args, **kwargs) -> tuple[BeautifulSoup, TargetInfo, str]:
        """
        抓取原始課表 HTML，並回傳 TargetInfo 與 url
        """
        target_info, url = await self._resolve_target_info(target, refresh=refresh)
        headers = self.get_headers()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                logger.debug(f"📡 發送請求：{target}")
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    content = await response.read()
                    logger.debug(f"📥 收到回應：{target}")
                    soup = BeautifulSoup(content, 'html.parser')
                    return soup, target_info, url
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

    def parse(self, soup: BeautifulSoup, target_info: TargetInfo, target_url: str, *args, **kwargs) -> TimetableSchema:
        """
        解析 BeautifulSoup 物件為結構化資料，支援午休課程分離。

        Args:
            soup (BeautifulSoup): HTML 解析樹
            target_info (TargetInfo): 目標資訊（含 id, role, category）
            target_url (str): 目標的課表連結

        Returns:
            TimetableSchema: 解析後的結構化資料

        Raises:
            FetchError: 當解析失敗時拋出
        """
        try:
            # 擷取更新日期
            update_element = soup.find('p', class_='MsoNormal', align='center')
            if update_element:
                span = update_element.find('span').find('span')
                last_update = span.text if span else "No update date found."
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

            # 擷取 periods，並偵測午休
            periods: Dict[str, Tuple[str, str]] = {}
            lunch_break_periods: Dict[str, Tuple[str, str]] = {}
            lunch_break_col = None
            current_lesson_count:int = 0
            for row in main_table.find_all("tr"):
                result = self._parse_periods(row)
                if result:
                    current_lesson_count += 1
                    lesson_name, times = result
                    # 午休關鍵字偵測
                    if "午休" in lesson_name:
                        lunch_break_col = current_lesson_count - 1  # 午休課程所在的列
                        lunch_break_periods[lesson_name] = times
                    else:
                        periods[lesson_name] = times

            if not lunch_break_periods:
                lunch_break_periods = None

            # 擷取 table raw 格式，並分離午休課程
            from tnfsh_timetable_core.timetable.models import CourseInfo
            table: List[List[CourseInfo | None]] = []
            lunch_break: List[CourseInfo | None] = []

            for i, row in enumerate(main_table.find_all("tr")):
                cells = row.find_all("td")[2:]  # 跳過前兩列（節次和時間）
                row_data = []
                for j, cell in enumerate(cells):
                    course = self._parse_cell(cell)
                    logger.debug(f"lunch_break_col: {lunch_break_col}, i: {i}, j: {j}")
                    # 若本行為午休節次，分離存入 lunch_break
                    if lunch_break_col is not None and i == lunch_break_col:
                        lunch_break.append(course)
                    else:
                        row_data.append(course)
                if row_data:
                    table.append(row_data)
            # 行列互換
            table = list(map(list, zip(*table)))

            
            if len(lunch_break) == 0:
                lunch_break = None
        except Exception as e:
            error_msg = f"解析錯誤：{str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FetchError(error_msg)
        # return 拿到 try 區塊外，避免 except 攔截 model 驗證錯誤
        return TimetableSchema(
            # TargetInfo 相關資訊
            target=target_info.target,
            category=target_info.category,
            target_url=target_info.url,
            role=target_info.role,
            id=target_info.id,
            # 其他資訊
            last_update=last_update,
            # 課表核心資料
            table=table,
            periods=periods,
            lunch_break=lunch_break,
            lunch_break_periods=lunch_break_periods,
        )

    async def fetch(self, target: str, refresh: bool = False, *args, **kwargs) -> TimetableSchema:
        """
        完整的課表抓取流程，TargetInfo 全程貫穿
        """
        soup, target_info, url = await self.fetch_raw(target, refresh=refresh)
        result = self.parse(soup, target_info=target_info, target_url=url)
        logger.info(f"✅ {target}({target_info.id})[抓取]完成")
        return result

if __name__ == "__main__":
    import asyncio
    async def main():
        crawler = TimetableCrawler()
        target = "陳暐捷"  # 替換為實際的班級或教師名稱
        timetable = await crawler.fetch(target, refresh=True)
        with open(f"{target}_timetable.json", "w", encoding="utf-8") as f:
            f.write(timetable.model_dump_json(indent=4))

        from tnfsh_timetable_core.index.index import Index
        index = await Index.fetch(refresh=False)
        index["C101205.HTML"]

    asyncio.run(main())