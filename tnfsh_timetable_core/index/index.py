"""台南一中課表系統的索引管理器"""

from typing import List
from datetime import datetime
from typing import Dict, Optional
from tnfsh_timetable_core.abc.domain_abc import BaseDomainABC
from tnfsh_timetable_core.index.models import IndexResult, ReverseIndexResult, AllTypeIndexResult
from tnfsh_timetable_core.index.cache import IndexCache
from tnfsh_timetable_core.index.crawler import IndexCrawler
from tnfsh_timetable_core.utils.logger import get_logger

import json

logger = get_logger(logger_level="INFO")

class Index(BaseDomainABC):
    """台南一中課表索引管理類別"""
    
    def __init__(
        self, 
        *,
        index: Optional[IndexResult] = None,
        reverse_index: Optional[ReverseIndexResult] = None,
        base_url: str = "http://w3.tnfsh.tn.edu.tw/deanofstudies/course/"
    ) -> None:
        """初始化索引管理器
        
        Args:
            index: 正向索引，可選
            reverse_index: 反向索引，可選
            base_url: 課表系統基礎 URL
        """
        # 公開屬性
        self.base_url = base_url
        self.index: IndexResult| None = index
        self.reverse_index: ReverseIndexResult| None = reverse_index

        # 私有屬性
        self._cache = IndexCache()
        self._crawler = IndexCrawler(base_url=base_url)

    @classmethod
    async def fetch(cls, *, refresh: bool = False, base_url: Optional[str] = None) -> "Index":
        """從快取或網路獲取索引資料並建立實例
        
        Args:
            refresh: 是否強制更新快取
            base_url: 可選的基礎 URL
            
        Returns:
            Index: 包含索引資料的實例
        """
        if refresh:
            logger.info("🔄 正在強制更新Index資料...")
        
        # 建立實例
        instance = cls(base_url=base_url or "http://w3.tnfsh.tn.edu.tw/deanofstudies/course/")
        
        # 獲取資料
        result = await instance._cache.fetch(refresh=refresh)
        instance.index = result.index
        instance.reverse_index = result.reverse_index
        
        logger.info(f"✅ Index載入完成！")
        return instance

    def export_json(self, export_type: str = "all", filepath: Optional[str] = None) -> str:
        """匯出索引資料為 JSON 格式
        
        Args:
            export_type: 要匯出的資料類型 ("index"/"reverse_index"/"all"，預設為 "all")
            filepath: 輸出檔案路徑，若未指定則自動生成
            
        Returns:
            str: 實際儲存的檔案路徑
            
        Raises:
            ValueError: 當 export_type 不合法時
            RuntimeError: 當尚未載入索引資料時
            Exception: 當檔案寫入失敗時
        """
        if self.index is None or self.reverse_index is None:
            raise RuntimeError("尚未載入索引資料")
            
        # 驗證 export_type
        valid_types = ["index", "reverse_index", "all"]
        if export_type.lower() not in valid_types:
            raise ValueError(f"不支援的匯出類型。請使用 {', '.join(valid_types)}")
        
        if export_type == "all":
            export_type = "index_all"
            
        # 準備要匯出的資料
        export_data = {}
        if export_type.lower() == "index":
            export_data["index"] = self.index.model_dump()
        elif export_type.lower() == "reverse_index":
            export_data["reverse_index"] = self.reverse_index.model_dump()
        else:  # all
            export_data = {
                "index": self.index.model_dump(),
                "reverse_index": self.reverse_index.model_dump()
            }

        # 加入匯出時間
        export_data["export_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 如果未指定檔案路徑，則自動生成
        if filepath is None:
            filepath = f"tnfsh_class_table_{export_type}.json"

        # 寫入 JSON 檔案
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 已匯出索引資料至 {filepath}")
            return filepath
        except Exception as e:
            raise Exception(f"寫入 JSON 檔案失敗: {str(e)}")

    def __getitem__(self, key: str) -> str:
        """快速查詢任何教師或班級的課表 URL
        
        Args:
            key: 教師名稱或班級代碼
            
        Returns:
            str: 課表的完整 URL
            
        Raises:
            KeyError: 當找不到指定的教師或班級時
            RuntimeError: 當尚未載入索引資料時
        """
        if self.reverse_index is None:
            raise RuntimeError("尚未載入索引資料")
        
        try:
            return f"{self.base_url}{self.reverse_index[key]['url']}"
        except KeyError:
            raise KeyError(f"找不到 {key} 的課表")
    
    def get_all_categories(self) -> List[str]:
        """獲取所有教師的分類科目列表"""
        if self.index is None:
            raise RuntimeError("尚未載入Index資料")
        return list(self.index.teacher.data.keys())
    
    def get_all_grades(self) -> List[str]:
        """獲取年級列表"""
        if self.index is None:
            raise RuntimeError("尚未載入Index資料")
        return list(self.index.class_.data.keys())

    def get_all_teachers(self) -> List[str]:
        """獲取所有教師的名稱列表"""
        if self.index is None:
            raise RuntimeError("尚未載入Index資料")
        result = []
        for category_name, teachers in self.index.teacher.data.items():
            result.extend(teachers.keys())
        return result
    
    def get_all_classes(self) -> List[str]:
        """獲取所有班級的代碼列表"""
        if self.index is None:
            raise RuntimeError("尚未載入Index資料")
        result = []
        for category_name, classes in self.index.class_.data.items():
            result.extend(classes.keys())
        return result
    