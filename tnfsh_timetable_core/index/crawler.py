from typing import Optional, Dict, Tuple
from unittest.mock import DEFAULT
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

from tnfsh_timetable_core.abc.crawler_abc import BaseCrawlerABC
from tnfsh_timetable_core.index.models import IndexResult, GroupIndex
from tnfsh_timetable_core import TNFSHTimetableCore

core = TNFSHTimetableCore()
logger = core.get_logger(logger_level="DEBUG")

class IndexCrawler(BaseCrawlerABC):
    """首頁索引爬蟲，負責獲取課表首頁的索引資訊"""

    DEFAULT_BASE_URL = "http://w3.tnfsh.tn.edu.tw/deanofstudies/course"
    DEFAULT_TEACHER_PAGE = "_TeachIndex.html"
    DEFAULT_CLASS_PAGE = "_ClassIndex.html"
    DEFAULT_ROOT = "index.html"

    def __init__(self, 
                 base_url: Optional[str] = None,
                 root_page: Optional[str] = None,
                 teacher_page: Optional[str] = None,
                 class_page: Optional[str] = None
                 ):
        """
        初始化爬蟲
        
        Args:
            base_url: 基礎 URL，如果未指定則使用預設值
        """
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.root = root_page or self.DEFAULT_ROOT
        self.teacher_page = teacher_page or self.DEFAULT_TEACHER_PAGE
        self.class_page = class_page or self.DEFAULT_CLASS_PAGE
        

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((
            aiohttp.ClientError,
            aiohttp.ServerTimeoutError,
            asyncio.TimeoutError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def fetch_raw(
        self,
        url: str,
        *,
        from_file: Optional[str] = None,
        timeout: int = 15
    ) -> BeautifulSoup:
        """獲取原始 HTML 內容
        
        Args:
            url: 相對 URL 路徑
            from_file: 可選的本地文件路徑
            timeout: 請求超時時間（秒）
            
        Returns:
            BeautifulSoup: 解析後的 HTML
            
        Raises:
            aiohttp.ClientError: 當發生網路錯誤時
            asyncio.TimeoutError: 當請求超時時
        """
        if from_file:
            logger.debug(f"📂 從檔案讀取：{from_file}")
            with open(from_file, 'r', encoding='utf-8') as f:
                return BeautifulSoup(f.read(), 'html.parser')
        
        logger.debug(f"🌐 請求網址：{url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.get_headers(),
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                response.raise_for_status()
                content = await response.read()
                logger.debug(f"📥 收到回應：{len(content)} bytes")
                return BeautifulSoup(content, 'html.parser')

    def parse(self, raw: BeautifulSoup, url: str) -> GroupIndex:
        """解析 HTML 內容為索引結構
        
        Args:
            raw: BeautifulSoup 物件
            url: 索引的相對 URL
            
        Returns:
            GroupIndex: 解析後的索引資料
        """
        parsed_data: Dict[str, Dict[str, str]] = {}
        current_category = None
        
        for tr in raw.find_all("tr"):
            # 處理分類標題
            if self._is_category_row(tr):
                current_category = tr.find("span").text.strip()
                parsed_data[current_category] = {}
                continue
            
            # 處理分類內容
            if current_category:
                self._process_links(tr, current_category, parsed_data)
        
        return GroupIndex(url=url, data=parsed_data)
    
    def _is_category_row(self, tr: BeautifulSoup) -> bool:
        """判斷是否為分類標題行"""
        return bool(tr.find("span") and not tr.find("a"))
    
    def _process_links(
        self,
        tr: BeautifulSoup,
        category: str,
        data: Dict[str, Dict[str, str]]
    ) -> None:
        """處理表格行中的連結"""
        for a in tr.find_all("a"):
            link = a.get("href")
            if not link:
                continue
                
            text = a.text.strip()
            if text.isdigit():
                # 班級代碼
                data[category][text] = link
            else:
                # 教師名稱或其他
                clean_text = self._clean_text(text)
                if clean_text:
                    data[category][clean_text] = link
    
    def _clean_text(self, text: str) -> Optional[str]:
        """清理並格式化文字"""
        # 嘗試提取中文名稱
        match = re.search(r'([\u4e00-\u9fa5]+)', text)
        if match:
            return match.group(1)
        
        # 處理其他格式
        text = text.replace("\r", "").replace("\n", "").replace(" ", "").strip()
        if len(text) > 3:
            return text[3:].strip()
        return None


    
    async def _fetch_all_pages(self) -> Tuple[BeautifulSoup, BeautifulSoup]:
        """並行獲取所有需要的頁面"""

        tasks = [
            self.fetch_raw(f"{self.base_url}/{self.teacher_page}"),
            self.fetch_raw(f"{self.base_url}/{self.class_page}")
        ]
        return await asyncio.gather(*tasks)
    
    def _create_index_result(
        self,
        teacher_soup: BeautifulSoup,
        class_soup: BeautifulSoup
    ) -> IndexResult:
        """創建索引結果"""
        return IndexResult(
            base_url=self.base_url,
            root=self.root,
            class_=self.parse(raw=class_soup, url=self.class_page),
            teacher=self.parse(raw=teacher_soup, url=self.teacher_page)
        )
    
    async def fetch(self, *, refresh: bool = False) -> IndexResult:
        """獲取完整的索引資料
        
        Args:
            refresh: 是否強制更新快取
            
        Returns:
            IndexResult: 完整的索引資料
        """
        # 並行獲取教師和班級索引
        teacher_soup, class_soup = await self._fetch_all_pages()
        
        # 解析資料並返回結果
        result = self._create_index_result(teacher_soup, class_soup)
        logger.info(f"✅ Index[抓取]完成")
        return result