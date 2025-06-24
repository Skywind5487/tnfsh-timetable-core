from typing import Optional
from datetime import datetime
from pathlib import Path
import json
from tnfsh_timetable_core.abc.cache_abc import BaseCacheABC
from tnfsh_timetable_core.index.models import (
    CachedFullIndex,
    CacheMetadata,
    FullIndexResult
)
from tnfsh_timetable_core.index.crawler import IndexCrawler
from tnfsh_timetable_core.utils.logger import get_logger


logger = get_logger(logger_level="INFO")

_memory_cache: Optional[CachedFullIndex] = None

class IndexCache(BaseCacheABC):
    """
    Index 快取層，支援三層快取（記憶體、檔案、網路來源）
    - 檔案快取預設為 prebuilt_full_index.json
    - 全域記憶體快取只存一份
    - 來源由 IndexCrawler 提供
    """
    def __init__(
        self,
        crawler: Optional[IndexCrawler] = None,
        file_path: Optional[str] = None
    ):
        """
        初始化 IndexCache
        Args:
            crawler: 索引爬蟲實例，預設自動建立
            file_path: 快取檔案路徑，預設為 prebuilt_full_index.json
        """
        self._crawler = crawler or IndexCrawler()
        self._cache_dir = Path(__file__).resolve().parent / "cache"
        self._cache_file = self._cache_dir / "prebuilt_full_index.json" if file_path is None else Path(file_path)
        self._cache_dir.mkdir(exist_ok=True)

    async def fetch_from_memory(self, *args, **kwargs) -> Optional[CachedFullIndex]:
        """
        從全域記憶體快取取得 Index
        Returns: CachedFullIndex 或 None
        """
        global _memory_cache
        if _memory_cache is not None:
            logger.debug("✨ 從全域記憶體快取取得Index")
            return _memory_cache
        return None

    async def save_to_memory(self, data: CachedFullIndex, *args, **kwargs) -> None:
        """
        儲存 Index 到全域記憶體快取
        """
        global _memory_cache
        _memory_cache = data
        logger.debug("✨ 已更新Index的全域記憶體快取")

    async def fetch_from_file(self, *args, **kwargs) -> Optional[CachedFullIndex]:
        """
        從檔案快取取得 Index
        Returns: CachedFullIndex 或 None
        """
        try:
            if not self._cache_file.exists():
                return None
            with open(self._cache_file, encoding="utf-8") as f:
                data = json.load(f)
                cached_data = CachedFullIndex.model_validate(data)
                logger.debug("💾 從檔案載入 Index 快取")
                return cached_data
        except Exception as e:
            logger.error(f"讀取快取檔案時發生錯誤: {e}")
            return None

    async def save_to_file(self, data: CachedFullIndex, *args, **kwargs) -> None:
        """
        儲存 Index 到檔案快取
        """
        try:
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json_data = data.model_dump_json(indent=4)
                f.write(json_data)
                logger.debug("💾 已更新 Index 檔案快取")
        except Exception as e:
            logger.error(f"儲存快取檔案時發生錯誤: {e}")
            raise

    async def fetch_from_source(self, *args, **kwargs) -> CachedFullIndex:
        """
        從網路來源取得最新 Index
        Returns: CachedFullIndex
        """
        logger.info("🌐 從網路抓取 Index")
        result: FullIndexResult = await self._crawler.fetch()
        return CachedFullIndex(
            metadata=CacheMetadata(cache_fetch_at=datetime.now()),
            data=result
        )

    async def fetch(self, *, refresh: bool = False, **kwargs) -> CachedFullIndex:
        """
        智能獲取 Index，依序嘗試記憶體、檔案、來源
        Returns: CachedFullIndex
        """
        if not refresh:
            mem = await self.fetch_from_memory()
            if mem:
                return mem
        if not refresh:
            file = await self.fetch_from_file()
            if file:
                await self.save_to_memory(file)
                return file
        net = await self.fetch_from_source()
        await self.save_to_file(net)
        await self.save_to_memory(net)
        return net
    

if __name__ == "__main__":
    import asyncio
    cache =  IndexCache()
    
    asyncio.run(cache.fetch(refresh=True))