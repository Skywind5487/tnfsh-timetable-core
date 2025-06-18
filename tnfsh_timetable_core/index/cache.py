from logging import log
from typing import Optional
from datetime import datetime
from pathlib import Path
import json
from tnfsh_timetable_core.abc.cache_abc import BaseCacheABC
from tnfsh_timetable_core.index.models import (
    IndexResult, 
    AllTypeIndexResult, 
    ReverseIndexResult,
    CacheMetadata,
    CachedIndexResult
)
from tnfsh_timetable_core.index.crawler import IndexCrawler
from tnfsh_timetable_core.utils.logger import get_logger

logger = get_logger(logger_level="INFO")

# 全域記憶體快取
_memory_cache: Optional[CachedIndexResult] = None

class IndexCache(BaseCacheABC):
    """課表系統索引的快取實作，支援三層快取架構"""
    
    def __init__(self, crawler: Optional[IndexCrawler] = None, file_path: Optional[str] = None):
        """初始化快取系統
        
        Args:
            crawler: 索引爬蟲實例，如果未提供會建立新的實例
            file_path: 快取檔案路徑，如果未提供則使用預設路徑
        """
        self._crawler = crawler or IndexCrawler()
        self._cache_dir = Path(__file__).resolve().parent / "cache"
        self._cache_file = self._cache_dir / "prebuilt_all_index.json" if file_path is None else Path(file_path)
        self._cache_dir.mkdir(exist_ok=True)

    async def fetch_from_memory(self, *args, **kwargs) -> Optional[CachedIndexResult]:
        """從全域變數快取取得索引資料
        
        Returns:
            Optional[CachedIndexResult]: 快取的索引資料，如果不存在則為 None
        """
        global _memory_cache
        if _memory_cache is not None:
            logger.debug("✨ 從全域記憶體快取取得Index")
            return _memory_cache
        return None

    async def save_to_memory(self, data: CachedIndexResult, *args, **kwargs) -> None:
        """儲存索引資料到全域變數快取
        
        Args:
            data: 要儲存的索引資料
        """
        global _memory_cache
        _memory_cache = data
        logger.debug("✨ 已更新Index的全域記憶體快取")

    async def fetch_from_file(self, *args, **kwargs) -> Optional[CachedIndexResult]:
        """從檔案快取取得索引資料
        
        Returns:
            Optional[CachedIndexResult]: 快取的索引資料，如果不存在或讀取失敗則為 None
        """
        try:
            if not self._cache_file.exists():
                return None
                
            with open(self._cache_file, encoding="utf-8") as f:
                data = json.load(f)
                result = CachedIndexResult.model_validate(data)
                logger.debug("💾 從檔案載入Index快取")
                return result
        except Exception as e:
            logger.error(f"讀取快取檔案時發生錯誤: {e}")
            return None

    async def save_to_file(self, data: CachedIndexResult, *args, **kwargs) -> None:
        """儲存索引資料到檔案快取
        
        Args:
            data: 要儲存的索引資料
        """
        try:
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json_data = data.model_dump_json(indent=4)
                f.write(json_data)
                logger.debug("💾 已更新Index檔案快取")
        except Exception as e:
            logger.error(f"儲存快取檔案時發生錯誤: {e}")
            raise

    def _create_reverse_index(self, index: IndexResult) -> ReverseIndexResult:
        """從正向索引建立反向索引
        
        Args:
            index: 索引資料
            
        Returns:
            ReverseIndexResult: 反向索引資料
        """
        reverse_data = {}
        
        # 處理教師資料
        for category, items in index.teacher.data.items():
            for name, url in items.items():
                reverse_data[name] = {"url": url, "category": category}
                
        # 處理班級資料
        for category, items in index.class_.data.items():
            for code, url in items.items():
                reverse_data[code] = {"url": url, "category": category}
                
        return ReverseIndexResult.model_validate(reverse_data)

    async def fetch_from_source(self, *args, **kwargs) -> CachedIndexResult:
        """從網路來源取得最新的索引資料
        
        Returns:
            CachedIndexResult: 包含正向和反向索引的完整索引資料
        """
        logger.info("🌐 從網路抓取Index")
        index = await self._crawler.fetch(refresh=True)
        reverse_index = self._create_reverse_index(index)
        
        return CachedIndexResult(
            metadata=CacheMetadata(cache_fetch_at=datetime.now()),
            data=AllTypeIndexResult(
                index=index,
                reverse_index=reverse_index
            )
        )

    async def fetch(self, *, refresh: bool = False, **kwargs) -> CachedIndexResult:
        """智能獲取索引資料，自動處理三層快取
        
        Args:
            refresh: 是否強制更新快取
            **kwargs: 傳遞給底層方法的額外參數
            
        Returns:
            CachedIndexResult: 完整的索引資料
        """
        return await super().fetch(refresh=refresh, **kwargs)
