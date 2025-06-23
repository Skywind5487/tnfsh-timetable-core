"""台南一中課表系統的索引管理器"""

from typing import TYPE_CHECKING, Dict, List, Optional
from datetime import datetime
import json
from tnfsh_timetable_core.index.models import (
    DetailedIndex,
    IndexResult, 
    ReverseIndexResult, 
    TargetInfo
)
from tnfsh_timetable_core.abc.domain_abc import BaseDomainABC
from tnfsh_timetable_core.utils.logger import get_logger

logger = get_logger(logger_level="INFO")

class Index(BaseDomainABC):
    """台南一中課表索引管理類別"""
    
    def __init__(
        self, 
        *,
        index: Optional[IndexResult] = None,
        reverse_index: Optional[ReverseIndexResult] = None,
        detail_index: DetailedIndex | None = None,
        id_to_info: Dict[str, TargetInfo] | None = None,
        target_to_unique_info: Dict[str, TargetInfo] | None = None,
        target_to_conflicting_ids: Dict[str, List[str]] | None = None,
        cache_fetch_at: Optional[datetime] = None,
        base_url: str = "http://w3.tnfsh.tn.edu.tw/deanofstudies/course/"
    ) -> None:
        """初始化索引管理器
        
        Args:
            index: 正向索引，可選
            reverse_index: 反向索引，可選
            cache_fetch_at: 快取抓取時間，可選
            base_url: 課表系統基礎 URL
        """
        # 公開屬性
        self.base_url = base_url
        # deprecated
        self.index: IndexResult | None = index
        self.reverse_index: ReverseIndexResult | None = reverse_index


        # new
        self.cache_fetch_at: datetime | None = cache_fetch_at
        self.detailed_index: DetailedIndex | None = detail_index
        self.id_to_info: Dict[str, TargetInfo] | None = id_to_info
        self.target_to_unique_info: Dict[str, TargetInfo] | None = target_to_unique_info
        self.target_to_conflicting_ids: Dict[str, List[str]] | None = target_to_conflicting_ids
        
        from tnfsh_timetable_core.index.cache import IndexCache
        from tnfsh_timetable_core.index.crawler import IndexCrawler
        # 私有屬性
        self._cache = IndexCache()
        self._crawler = IndexCrawler()

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
        cached_result = await instance._cache.fetch(refresh=refresh)

        # deprecated
        instance.index = cached_result.data.index
        instance.reverse_index = cached_result.data.reverse_index
        
        # new
        instance.detailed_index = cached_result.data.detailed_index
        instance.id_to_info =  cached_result.data.id_to_info
        instance.target_to_unique_info = cached_result.data.target_to_unique_info
        instance.target_to_conflicting_ids = cached_result.data.target_to_conflicting_ids
        instance.cache_fetch_at = cached_result.metadata.cache_fetch_at
        
        logger.debug(f"⏰ 快取抓取時間：{instance.cache_fetch_at}")
        logger.info("✅ Index[載入]完成！")
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
        from tnfsh_timetable_core.index.models import (
            CacheMetadata,
            CachedIndex,
            CachedReverseIndex,
            CachedFullIndex,
            FullIndexResult
        )
        if self.index is None or self.reverse_index is None:
            raise RuntimeError("尚未載入索引資料")
            
        # 驗證 export_type
        valid_types = ["index", "reverse_index", "all"]
        if export_type.lower() not in valid_types:
            raise ValueError(f"不支援的匯出類型。請使用 {', '.join(valid_types)}")
        
        # 準備元數據
        metadata = CacheMetadata(cache_fetch_at=self.cache_fetch_at or datetime.now())
        
        # 生成檔案路徑
        if filepath is None:
            filepath = f"index_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        # 寫入檔案
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                if export_type == "all":
                    f.write(CachedFullIndex(
                        metadata=metadata,
                        data=FullIndexResult(
                            index=self.index,
                            reverse_index=self.reverse_index,
                            detailed_index=self.detailed_index,
                            id_to_info=self.id_to_info or {},
                            target_to_unique_info=self.target_to_unique_info or {},
                            target_to_conflicting_ids=self.target_to_conflicting_ids or {}
                        )
                    ).model_dump_json(indent=4))
                elif export_type == "index":
                    f.write(CachedIndex(
                        metadata=metadata,
                        data=self.index
                    ).model_dump_json(indent=4))
                else:  # reverse_index
                    f.write(CachedReverseIndex(
                        metadata=metadata,
                        data=self.reverse_index
                    ).model_dump_json(indent=4))
                logger.debug(f"📝 索引資料已匯出至：{filepath}")
                logger.debug(f"⏰ 快取時間戳記：{metadata.cache_fetch_at}")
        except Exception as e:
            logger.error(f"❌ 匯出失敗：{str(e)}")
            raise
            
        return filepath

    def __getitem__(self, key: str) -> TargetInfo | List[str]:
        """
        快速查詢任何教師或班級的課表 TargetInfo
        推薦使用的方法
        
        Args:
            key: 教師名稱、班級代碼、或ID
            
        Returns:
            TargetInfo: 正確找到
            List[str]: 在contarget_to_conflicting_ids當中
            
        Raises:
            KeyError: 當找不到指定的教師或班級時
            RuntimeError: 當尚未載入索引資料時
        """
        from tnfsh_timetable_core.index.identify_index_key import get_fuzzy_target_info
        from tnfsh_timetable_core.index.models import FullIndexResult

        if (self.id_to_info is None or 
            self.target_to_unique_info is None or 
            self.target_to_conflicting_ids is None):
            raise RuntimeError("尚未載入索引資料")
        return get_fuzzy_target_info(
            key,
            FullIndexResult(
                index=self.index,
                reverse_index=self.reverse_index,
                detailed_index=self.detailed_index,
                id_to_info=self.id_to_info,
                target_to_unique_info=self.target_to_unique_info,
                target_to_conflicting_ids=self.target_to_conflicting_ids
            )
        )

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

    def get_all_targets(self) -> List[str]:
        """獲取所有教師和班級的名稱列表"""
        if self.reverse_index is None:
            raise RuntimeError("尚未載入Index資料")
        return list(self.reverse_index.keys())
    

if __name__ == "__main__":
    
    async def test_index():
        """測試索引功能"""
        index = await Index.fetch()
        print(index["顏永進"])  # 測試查詢教師
        print(index["J04"])
        print(index["119"])
        print(index["Nicole"])

        # 僅用 index 內實際存在的 target/ID/班級做測試
        examples = [
            "顏永進",    # target (teacher)
            "Nicole",    # target (teacher)
            "J04",       # teacher ID (短)
            "TJ04",      # teacher ID (全)
            "Z09",       # teacher ID (短)
            "TZ09",      # teacher ID (全)
            "119",       # class id_suffix
            "C108119"    # class id (全)
        ]
        for example in examples:
            try:
                result = index[example]
                print(result)
            except Exception as e:
                print(f"{example!r:15} → ❌ {e}")
    import asyncio
    asyncio.run(test_index())