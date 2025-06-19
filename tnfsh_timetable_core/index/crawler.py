from typing import Optional, Dict, Tuple, List
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
import json
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

from tnfsh_timetable_core.abc.crawler_abc import BaseCrawlerABC
from tnfsh_timetable_core.index.models import (
    AllTypeIndexResult,
    DetailedIndex,
    GroupIndex,
    IndexResult,
    NewCategoryMap,
    NewGroupIndex,
    NewItemMap,
    TargetInfo,
    ReverseIndexResult
)
from tnfsh_timetable_core import TNFSHTimetableCore

core = TNFSHTimetableCore()
logger = core.get_logger(logger_level="INFO")

class IndexCrawler(BaseCrawlerABC):    
    """首頁索引爬蟲，負責爬取、解析和組織課表系統的索引資訊
    
    資料流程：
    1. 原始資料獲取
       HTTP 請求 -> BeautifulSoup 物件
       傳入：URL
       輸出：parsed HTML
       
    2. 內容結構解析
       BeautifulSoup -> DetailedIndex
       傳入：HTML 內容
       輸出：結構化的分類映射
       
    3. 索引關係處理
       DetailedIndex -> 各式索引表
       - ID 對照表
       - 名稱映射（處理重複）
       - 舊版格式轉換
       
    4. 最終資料整合
       所有索引 -> AllTypeIndexResult
    
    元件依賴：
    1. 網路工具 (底層)
       fetch_raw: HTTP 請求處理
       _fetch_all_pages: 並行請求控制
    
    2. 資料操作 (中層)
       _clean_text: 文字正規化(無依賴)
       _is_category_row: 結構識別(無依賴)
       _parse_page: 頁面解析邏輯
       _derive_*: 索引處理工具
    
    3. 流程控制 (頂層)
       parse: 解析流程調度
       fetch: 主流程進入點
       
    備註：
    - 使用 DetailedIndex 作為核心資料結構
    - 支援新舊格式轉換，維持相容性
    - 實現並行請求，提升效能
    - 處理名稱衝突，確保索引正確
    """
    
    # ====================================
    # 🔧 基礎設定：系統配置和 URL 定義
    # ====================================

    # 課表系統基礎 URL，可透過 __init__ 覆寫
    DEFAULT_BASE_URL = "http://w3.tnfsh.tn.edu.tw/deanofstudies/course"
    
    # 索引頁面路徑，依據實際部署環境可能需要調整
    DEFAULT_TEACHER_PAGE = "_TeachIndex.html"  # 教師索引頁面
    DEFAULT_CLASS_PAGE = "_ClassIndex.html"    # 班級索引頁面
    DEFAULT_ROOT = "index.html"                # 根目錄頁面

    def __init__(
        self, 
        base_url: Optional[str] = None,
        root_page: Optional[str] = None,
        teacher_page: Optional[str] = None,
        class_page: Optional[str] = None
    ):
        """初始化爬蟲
        
        Args:
            base_url: 基礎 URL
            root_page: 根目錄頁面
            teacher_page: 教師索引頁面
            class_page: 班級索引頁面
        """        
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.root = root_page or self.DEFAULT_ROOT
        self.teacher_page = teacher_page or self.DEFAULT_TEACHER_PAGE
        self.class_page = class_page or self.DEFAULT_CLASS_PAGE    
    # ====================================
    # 🌐 網路請求：HTTP 通信和資料獲取
    # ====================================

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

    async def _fetch_all_pages(self) -> Tuple[BeautifulSoup, BeautifulSoup]:
        """並行獲取所有需要的頁面
        
        Returns:
            Tuple[BeautifulSoup, BeautifulSoup]: (教師頁面, 班級頁面)
        """
        tasks = [
            self.fetch_raw(f"{self.base_url}/{self.teacher_page}"),
            self.fetch_raw(f"{self.base_url}/{self.class_page}")
        ]
        return await asyncio.gather(*tasks)

    # ====================================
    # 📝 內容解析：HTML 解析與資料提取
    # ====================================

    def _clean_text(self, text: str) -> Optional[str]:
        """清理並格式化文字
        
        Args:
            text: 原始文字
            
        Returns:
            str | None: 清理後的文字，如果無法清理則返回 None
        """
        # 嘗試提取中文名稱
        match = re.search(r'([\u4e00-\u9fa5]+)', text)
        if match:
            return match.group(1)
        
        # 處理其他格式
        text = text.replace("\r", "").replace("\n", "").replace(" ", "").strip()
        if len(text) > 3:
            return text[3:].strip()
        return None

    def _is_category_row(self, tr: BeautifulSoup) -> bool:
        """判斷是否為分類標題行
        
        Args:
            tr: HTML表格行
            
        Returns:
            bool: 是否為分類標題
        """
        return bool(tr.find("span") and not tr.find("a"))    
    def _parse_page(
        self,
        raw: BeautifulSoup,
        is_teacher: bool
    ) -> NewCategoryMap:
        """解析單一頁面的內容並返回分類映射
        
        Args:
            raw: BeautifulSoup 物件
            is_teacher: 是否為教師頁面
            
        Returns:
            NewCategoryMap: 分類到 NewItemMap 的映射，其中 NewItemMap 是 ID 到 TargetInfo 的映射
        """
        # 初始化結果字典：分類 -> (ID -> TargetInfo)
        result: Dict[str, Dict[str, TargetInfo]] = {}
        current_category = None
        
        for tr in raw.find_all("tr"):
            # 處理分類標題
            if self._is_category_row(tr):
                current_category = tr.find("span").text.strip()
                result[current_category] = {}
                continue
                
            # 處理分類內容
            if not current_category:
                continue
                
            for a in tr.find_all("a"):
                link = a.get("href")
                if not link:
                    continue
                    
                # 提取基本資訊
                raw_name = a.text.strip()
                clean_name = self._clean_text(raw_name) if is_teacher else raw_name
                if not clean_name:
                    continue
                    
                # 建立目標資訊
                info = TargetInfo(
                    target=clean_name,
                    category=current_category,
                    url=link
                )
                
                # 更新分類映射，使用 ID 作為鍵值
                result[current_category][info.id] = info
                    
        # 建立巢狀結構：先建立每個分類的 NewItemMap，再包成 NewCategoryMap
        category_map = {
            category: NewItemMap.model_validate(items)
            for category, items in result.items()
        }
        
        return NewCategoryMap.model_validate(category_map)

    # ====================================
    # 📊 索引處理：衍生索引的生成與管理
    # ====================================

    def _derive_id_to_info(self, detailed: DetailedIndex) -> Dict[str, TargetInfo]:
        """從 detailed_index 派生 id_to_info 映射
        
        Args:
            detailed: 詳細索引
            
        Returns:
            Dict[str, TargetInfo]: ID 到目標資訊的映射
        """
        result: Dict[str, TargetInfo] = {}
        
        # 從教師和班級索引派生
        for group in (detailed.teacher.data, detailed.class_.data):
            for category in group:
                for info in group[category].values():
                    result[info.id] = info
                
        return result

    def _derive_name_mappings(
        self, 
        detailed: DetailedIndex
    ) -> Tuple[Dict[str, TargetInfo], Dict[str, List[str]]]:
        """從 detailed_index 派生名稱相關的映射
        
        處理邏輯：
        1. 如果名稱已在衝突表中，直接加入新的 ID
        2. 如果名稱已有唯一映射，則將原有映射移至衝突表
        3. 如果名稱尚未出現，新增唯一映射
        
        Args:
            detailed: 詳細索引
            
        Returns:
            Tuple[Dict[str, TargetInfo], Dict[str, List[str]]]: 
            - name_to_unique_info: 唯一名稱到目標資訊的映射
            - name_to_conflicting_ids: 重複名稱到 ID 列表的映射
        """
        name_to_unique_info: Dict[str, TargetInfo] = {}
        name_to_conflicting_ids: Dict[str, List[str]] = {}
        
        def process_info(info: TargetInfo) -> None:
            """處理單一目標資訊的名稱映射"""
            if info.target in name_to_conflicting_ids:
                # 如果已在衝突表中，直接加入 ID
                name_to_conflicting_ids[info.target].append(info.id)
            elif info.target in name_to_unique_info:
                # 如果已有唯一映射，移至衝突表
                name_to_conflicting_ids[info.target] = [
                    name_to_unique_info[info.target].id,
                    info.id
                ]
                del name_to_unique_info[info.target]
            else:
                # 新增唯一映射
                name_to_unique_info[info.target] = info
        
        # 處理所有教師和班級的目標資訊
        for data in (detailed.teacher.data, detailed.class_.data):
            for category in data:
                for info in data[category].values():
                    process_info(info)
                
        return name_to_unique_info, name_to_conflicting_ids

    def _derive_old_index(self, detailed: DetailedIndex) -> IndexResult:
        """從 detailed_index 派生舊格式的索引結果
        
        處理邏輯：
        1. 檢查每個 target 是否有衝突
        2. 如果有衝突，在目標名稱後加上 ID，如 "王小明(A01)"
        3. 如果無衝突，直接使用原始名稱
        
        Args:
            detailed: 詳細索引
            
        Returns:
            IndexResult: 舊格式的索引結果
        """
        # 先取得衝突映射
        _, name_to_conflicting_ids = self._derive_name_mappings(detailed)
        
        def get_display_name(info: TargetInfo) -> str| None:
            """根據衝突情況取得顯示名稱"""
            if info.target in name_to_conflicting_ids:
                return None
            return info.target
        
        # 轉換教師和班級資料
        result = {
            "teacher": {},
            "class": {}
        }
        
        # 處理教師和班級索引
        for group_name, group_data in (
            ("teacher", detailed.teacher.data),
            ("class", detailed.class_.data)
        ):
            for category, infos in group_data.items():
                result[group_name][category] = {
                    display_name: info.url
                    for info in infos.values()
                    if (display_name := get_display_name(info)) is not None
                }
                
        return IndexResult(
            base_url=self.base_url,
            root=self.root,
            class_=GroupIndex(url=f"{self.class_page}", data=result["class"]),
            teacher=GroupIndex(url=f"{self.teacher_page}", data=result["teacher"])
        )
    
    def _derive_old_reverse_index(self, detailed: DetailedIndex) -> ReverseIndexResult:
        """從 detailed_index 派生舊版反向索引
        處理邏輯：
        1. 直接從 detailed_index 的分類和目標資訊建立反向索引
        2. 每個目標名稱對應到其 URL 和分類
        Args:
            detailed: 詳細索引
        Returns:    
            ReverseIndexResult: 反向索引結果
        """
        result: Dict[str, Dict[str, str]] = {} # {target_name: {"url": <url>, "category": <category>}}
        _, name_to_conflicting_ids = self._derive_name_mappings(detailed)
        
        def get_display_name(info: TargetInfo) -> str| None:
            """根據衝突情況取得顯示名稱"""
            if info.target in name_to_conflicting_ids:
                return None
            return info.target

        # 處理教師和班級索引
        for group_name, group_data in (
            ("teacher", detailed.teacher.data),
            ("class", detailed.class_.data)
        ):
            for category, infos in group_data.items():
                for info in infos.values():
                    display_name = get_display_name(info)
                    if display_name is not None:
                        result[display_name] = {
                            "url": info.url,
                            "category": category
                        }

        return ReverseIndexResult.model_validate(result)

    # ====================================
    # 🔄 主要流程：最終處理和流程控制
    # ====================================
    
    def parse(
        self, 
        teacher_raw: BeautifulSoup, 
        class_raw: BeautifulSoup
    ) -> AllTypeIndexResult:
        """解析教師和班級的原始資料，並建立完整的索引結構
        
        此方法整合了所有解析和索引處理流程，是主要的邏輯控制中心。
        依賴所有其他解析和索引處理方法。
        
        流程：
        1. 使用 _parse_page 解析原始頁面，生成 detailed_index
        2. 使用 _derive_* 方法從 detailed_index 派生所有其他索引
           - ID 對照表
           - 名稱映射（處理重複名稱）
           - 舊版格式相容

        Args:
            teacher_raw: 教師頁面的 BeautifulSoup 物件
            class_raw: 班級頁面的 BeautifulSoup 物件
            
        Returns:
            AllTypeIndexResult: 完整的索引結果，包含：
            - detailed_index: 詳細索引資訊
            - id_to_info: ID 映射
            - name_*: 名稱相關映射
            - index: 舊版格式索引
        """
        # 第一階段：解析原始頁面，建立 detailed_index
        teacher_detailed = self._parse_page(teacher_raw, is_teacher=True)
        class_detailed = self._parse_page(class_raw, is_teacher=False)

        # 合併為完整的 detailed_index
        detailed = DetailedIndex(
            base_url=self.base_url,
            root=self.root,
            teacher=NewGroupIndex(data=teacher_detailed, url=f"{self.teacher_page}"),
            class_=NewGroupIndex(data=class_detailed, url=f"{self.class_page}")
        )

        # 第二階段：從 detailed_index 派生其他索引
        id_to_info = self._derive_id_to_info(detailed)
        name_to_unique_info, name_to_conflicting_ids = self._derive_name_mappings(detailed)
        old_index = self._derive_old_index(detailed)
        old_reverse_index = self._derive_old_reverse_index(detailed) 
        
        # 最終階段：組裝完整結果
        return AllTypeIndexResult(
            index=old_index,
            reverse_index=old_reverse_index,
            detailed_index=detailed,
            id_to_info=id_to_info,
            name_to_unique_info=name_to_unique_info,
            name_to_conflicting_ids=name_to_conflicting_ids
        )

    async def fetch(self) -> AllTypeIndexResult:
        """取得完整的索引結果
        
        此方法是整個爬蟲的最高層級入口，整合了所有功能：
        1. 網路請求
        2. 內容解析
        3. 索引處理
        
        依賴鏈：
        - _fetch_all_pages (網路請求)
        - parse (解析和索引)
          |- _parse_page (頁面解析)
          |- _derive_* (索引處理)
        
        Returns:
            AllTypeIndexResult: 完整的索引結果
        """
        # 第一階段：並行獲取教師和班級索引頁面
        teacher_soup, class_soup = await self._fetch_all_pages()
        
        # 第二階段：解析並建立完整的索引結構
        result = self.parse(teacher_raw=teacher_soup, class_raw=class_soup)
        logger.info("✅ Index[抓取]完成")
        return result
    
if __name__ == "__main__":
    # 測試用例：直接運行爬蟲
    async def main():
        crawler = IndexCrawler()
        result = await crawler.fetch()
        with open("index_result.json", "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=4, exclude_none=False))
        print(result.model_dump_json(indent=4, exclude_none=False))

    asyncio.run(main())