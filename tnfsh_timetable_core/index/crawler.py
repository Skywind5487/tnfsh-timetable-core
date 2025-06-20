from math import log
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
from functools import cache

from tnfsh_timetable_core.abc.crawler_abc import BaseCrawlerABC
from tnfsh_timetable_core.index.models import (
    FullIndexResult,
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
       所有索引 -> FullIndexResult
    
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
    DEFAULT_ROOT = "course.html"                # 根目錄頁面

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

    async def _fetch_all_pages(self) -> Tuple[BeautifulSoup, BeautifulSoup, BeautifulSoup]:
        """優化：先抓 root，再決定是否重抓 teacher/class

        Returns:
            Tuple: (root, teacher, class)
        """

        # 並行抓 root / 預設 teacher / 預設 class（如果沒被注入）
        logger.debug("📥 開始併發抓取 root + teacher/class 頁面")
        root_task = self.fetch_raw(f"{self.base_url}/{self.root}")

        teacher_task = None
        class_task = None
        if not self.teacher_page:
            logger.debug("🧩 teacher_page 未注入，使用預設值")
            teacher_task = self.fetch_raw(f"{self.base_url}/{self.DEFAULT_TEACHER_PAGE}")
        else:
            logger.debug(f"✅ teacher_page 已注入：{self.teacher_page}")
            teacher_task = self.fetch_raw(f"{self.base_url}/{self.teacher_page}")

        if not self.class_page:
            logger.debug("🧩 class_page 未注入，使用預設值")
            class_task = self.fetch_raw(f"{self.base_url}/{self.DEFAULT_CLASS_PAGE}")
        else:
            logger.debug(f"✅ class_page 已注入：{self.class_page}")
            class_task = self.fetch_raw(f"{self.base_url}/{self.class_page}")

        root_soup, teacher_soup, class_soup = await asyncio.gather(
            root_task,
            teacher_task,
            class_task,
            return_exceptions=True  # ✅ 讓錯誤變成例外物件傳回

        )

        logger.debug("📖 root 頁面抓取完成，開始解析")
        root_teacher_url, root_class_url, last_update = self._parse_root(root_soup)

        # 若未注入，檢查是否需 fallback 重抓
        if not self.teacher_page or isinstance(teacher_soup, Exception):
            if root_teacher_url != self.DEFAULT_TEACHER_PAGE or isinstance(teacher_soup, Exception):
                logger.warning(f"🔁 root 指定的 teacher_url（{root_teacher_url}）與預設不同，重新抓取")
                teacher_soup = await self.fetch_raw(f"{self.base_url}/{root_teacher_url}")
            else:
                logger.debug("✅ root teacher_url 與預設一致，使用預抓內容")
            self.teacher_page = root_teacher_url

        if not self.class_page or isinstance(class_soup, Exception):
            if root_class_url != self.DEFAULT_CLASS_PAGE or isinstance(class_soup, Exception):
                logger.warning(f"🔁 root 指定的 class_url（{root_class_url}）與預設不同，重新抓取")
                class_soup = await self.fetch_raw(f"{self.base_url}/{root_class_url}")
            else:
                logger.debug("✅ root class_url 與預設一致，使用預抓內容")
            self.class_page = root_class_url

        logger.debug("✅ 所有index頁面準備完成")
        return root_soup, teacher_soup, class_soup, last_update


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
    
    def _parse_root(
        self,
        raw: BeautifulSoup
    ) -> Tuple[str, str, str]: # Teacher_url, class_url, last_update
        """解析根目錄頁面以獲取教師和班級索引的 URL 以及最後更新時間"""
        # 班級:
        # tr style="mso-yfti-irow:1;height:36.0pt"
        # a
        # text == 班級索引一覽表
        # url->a
        # 教師: 相同
        # text == 教師索引一覽表
        # url->a
        # 更新日期
        # tr
        # span style="font-size:22.0pt;font-family:&quot;微軟正黑體&quot;,sans-serif;color:red"
        # span
        # text == 2023/10/01 12:00:00

        teacher_url = "_TeachIndex.html"
        class_url = "_ClassIndex.html"
        last_update = "No update date found."

        for tr in raw.find_all("tr"):
            # 處理教師索引
            if tr.find("span", string="教師索引一覽表"):
                a = tr.find("a")
                if a and a.get("href"):
                    teacher_url = a.get("href")
                    logger.debug(f"📚 教師索引 URL: {teacher_url}")
            # 處理班級索引
            elif tr.find("span", string="班級索引一覽表"):
                a = tr.find("a")
                if a and a.get("href"):
                    class_url = a.get("href")
                    logger.debug(f"📚 班級索引 URL: {class_url}")
            # 擷取更新日期
            elif tr.find("span", style=lambda s: s and "font-size:22.0pt" in s and "color:red" in s):
                span = tr.find("span")
                if span:
                    last_update = span.find("span").text
                    logger.debug(f"📅 root 的更新日期：{last_update}")
            if teacher_url and class_url and last_update != "No update date found.":
                break

        if not teacher_url or not class_url:
            logger.warning("⚠️ 找不到教師或班級索引 URL，將使用預設值")
        if not last_update:
            logger.warning("⚠️ 找不到更新日期，將使用預設值")
        return teacher_url, class_url, last_update

    def _parse_page(
        self,
        raw: BeautifulSoup,
        is_teacher: bool
    ) -> Tuple[NewCategoryMap, str]: # (分類映射, 最後更新時間)
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
        # 擷取更新日期
        update_element = raw.find('p', class_='MsoNormal', align='center')
        if update_element:
            spans = update_element.find_all('span')
            last_update = spans[1].text if len(spans) > 1 else "No update date found."
            logger.debug(f"📅 {"教師索引一覽表" if is_teacher else "班級索引一覽表"} 的更新日期：{last_update}")
        else:
            last_update = "No update date found."
            logger.warning("⚠️ 找不到更新日期") 

        # 建立巢狀結構：先建立每個分類的 NewItemMap，再包成 NewCategoryMap
        category_map = {
            category: NewItemMap.model_validate(items)
            for category, items in result.items()
        }
        return NewCategoryMap.model_validate(category_map), last_update
    

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
            - target_to_unique_info: 唯一名稱到目標資訊的映射
            - target_to_conflicting_ids: 重複名稱到 ID 列表的映射
        """
        target_to_unique_info: Dict[str, TargetInfo] = {}
        target_to_conflicting_ids: Dict[str, List[str]] = {}
        
        def process_info(info: TargetInfo) -> None:
            """處理單一目標資訊的名稱映射"""
            if info.target in target_to_conflicting_ids:
                # 如果已在衝突表中，直接加入 ID
                target_to_conflicting_ids[info.target].append(info.id)
            elif info.target in target_to_unique_info:
                # 如果已有唯一映射，移至衝突表
                target_to_conflicting_ids[info.target] = [
                    target_to_unique_info[info.target].id,
                    info.id
                ]
                del target_to_unique_info[info.target]
            else:
                # 新增唯一映射
                target_to_unique_info[info.target] = info
        
        # 處理所有教師和班級的目標資訊
        for data in (detailed.teacher.data, detailed.class_.data):
            for category in data:
                for info in data[category].values():
                    process_info(info)
                
        return target_to_unique_info, target_to_conflicting_ids

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
        _, target_to_conflicting_ids = self._derive_name_mappings(detailed)
        
        def get_display_name(info: TargetInfo) -> str| None:
            """根據衝突情況取得顯示名稱"""
            if info.target in target_to_conflicting_ids:
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
        _, target_to_conflicting_ids = self._derive_name_mappings(detailed)
        
        def get_display_name(info: TargetInfo) -> str| None:
            """根據衝突情況取得顯示名稱"""
            if info.target in target_to_conflicting_ids:
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
        class_raw: BeautifulSoup,
        root_last_update: str,
    ) -> FullIndexResult:
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
            FullIndexResult: 完整的索引結果，包含：
            - detailed_index: 詳細索引資訊
            - id_to_info: ID 映射
            - name_*: 名稱相關映射
            - index: 舊版格式索引
        """
        # 第一階段：解析原始頁面，建立 detailed_index
        last_update = root_last_update
        teacher_detailed, teacher_last_update = self._parse_page(teacher_raw, is_teacher=True)
        class_detailed, class_last_update = self._parse_page(class_raw, is_teacher=False)

        # 合併為完整的 detailed_index
        detailed = DetailedIndex(
            base_url=self.base_url,
            root=self.root,
            last_update=last_update,
            teacher=NewGroupIndex(data=teacher_detailed, url=f"{self.teacher_page}", last_update=teacher_last_update),
            class_=NewGroupIndex(data=class_detailed, url=f"{self.class_page}", last_update=class_last_update)
        )

        # 第二階段：從 detailed_index 派生其他索引
        id_to_info = self._derive_id_to_info(detailed)
        target_to_unique_info, target_to_conflicting_ids = self._derive_name_mappings(detailed)
        old_index = self._derive_old_index(detailed)
        old_reverse_index = self._derive_old_reverse_index(detailed) 
        
        # 最終階段：組裝完整結果
        return FullIndexResult(
            index=old_index,
            reverse_index=old_reverse_index,
            detailed_index=detailed,
            id_to_info=id_to_info,
            target_to_unique_info=target_to_unique_info,
            target_to_conflicting_ids=target_to_conflicting_ids
        )

    async def fetch(self) -> FullIndexResult:
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
            FullIndexResult: 完整的索引結果
        """
        # 第一階段：並行獲取教師和班級索引頁面
        _, teacher_soup, class_soup, root_last_update = await self._fetch_all_pages()
        
        # 第二階段：解析並建立完整的索引結構
        result = self.parse(teacher_raw=teacher_soup, class_raw=class_soup, root_last_update=root_last_update)
        logger.info("✅ Index[抓取]完成")
        return result
    
