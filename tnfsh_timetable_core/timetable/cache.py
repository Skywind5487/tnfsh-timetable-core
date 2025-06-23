import re
from typing import Dict, Optional
from datetime import datetime
import logging
import asyncio
from pathlib import Path
import json
from aiohttp import client_exceptions
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)

from tnfsh_timetable_core.abc.cache_abc import BaseCacheABC
from tnfsh_timetable_core.timetable.models import (
    CacheMetadata,
    CachedTimeTable, 
    TimetableSchema
)
from tnfsh_timetable_core.timetable.crawler import TimetableCrawler, FetchError
from tnfsh_timetable_core.utils.logger import get_logger
from pydantic import BaseModel

logger = get_logger(logger_level="INFO")



# 全域記憶體快取
_memory_cache: Dict[str, CachedTimeTable] = {}

class TimeTableCache(BaseCacheABC):
    """課表的快取實作，支援三層快取架構"""
    
    def __init__(
        self, 
        crawler: Optional[TimetableCrawler] = None,
        cache_dir: Optional[str] = None,
        file_path_template: str = "prebuilt_{target}.json"
    ):
        """初始化快取系統
        
        Args:
            crawler: 課表爬蟲實例，如果未提供會建立新的實例
            cache_dir: 快取目錄路徑，如果未提供則使用預設路徑
            file_path_template: 快取檔案名稱模板，可用 {target} 做替換
        """
        self._crawler = crawler or TimetableCrawler()
        self._cache_dir = Path(cache_dir) if cache_dir else Path(__file__).resolve().parent / "cache"
        self._file_path_template = file_path_template
        self._cache_dir.mkdir(exist_ok=True)

    def _get_cache_path(self, target: str) -> Path:
        """取得目標的快取檔案路徑
        
        Args:
            target: 目標名稱（班級或教師）
            
        Returns:
            Path: 快取檔案路徑
        """
        # 確保檔名安全
        safe_target = "".join(c for c in target if c.isalnum() or c in "-_")
        return self._cache_dir / self._file_path_template.format(target=safe_target)

    async def fetch_from_memory(self, target: str, *args, **kwargs) -> Optional[CachedTimeTable]:
        """從全域變數快取取得課表資料
        
        Args:
            target: 目標名稱（班級或教師）
            
        Returns:
            Optional[CachedTimeTable]: 快取的課表資料，如果不存在則為 None
        """
        if target in _memory_cache:
            logger.debug(f"✨ 從記憶體快取取得課表：{target}")
            return _memory_cache[target]
        return None

    async def save_to_memory(self, data: CachedTimeTable, target: str, *args, **kwargs) -> None:
        """儲存課表資料到全域變數快取
        
        Args:
            data: 要儲存的課表資料
            target: 目標名稱（班級或教師）
        """
        _memory_cache[target] = data
        logger.debug(f"✨ 已更新記憶體快取：{target}")

    async def fetch_from_file(self, target: str, *args, **kwargs) -> Optional[CachedTimeTable]:
        """從檔案快取取得課表資料
        
        Args:
            target: 目標名稱（班級或教師）
            
        Returns:
            Optional[CachedTimeTable]: 快取的課表資料，如果不存在或讀取失敗則為 None
        """
        cache_path = self._get_cache_path(target)
        try:
            if not cache_path.exists():
                return None
                
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)
                result = CachedTimeTable.model_validate(data)
                logger.debug(f"💾 從檔案載入課表快取：{target}")
                return result
        except Exception as e:
            logger.error(f"讀取快取檔案時發生錯誤: {e}")
            return None

    async def save_to_file(self, data: CachedTimeTable, target: str, *args, **kwargs) -> None:
        """儲存課表資料到檔案快取
        
        Args:
            data: 要儲存的課表資料
            target: 目標名稱（班級或教師）
        """
        cache_path = self._get_cache_path(target)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json_data = data.model_dump_json(indent=4)
                f.write(json_data)
                logger.debug(f"💾 已更新檔案快取：{target}")
        except Exception as e:
            logger.error(f"儲存快取檔案時發生錯誤: {e}")
            raise FetchError(f"儲存快取檔案失敗: {str(e)}")
    
    @retry(
        retry=retry_if_exception_type((
            FetchError,
            client_exceptions.ClientError,
            client_exceptions.ServerTimeoutError,
            asyncio.TimeoutError
        )),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def fetch_from_source(self, target: str, *args, **kwargs) -> CachedTimeTable:
        """從網路來源取得最新的課表資料
        
        Args:
            target: 目標名稱（班級或教師）
            
        Returns:
            CachedTimeTable: 包含最新課表資料的快取結構
        """
        try:
            logger.info(f"🌐 從網路抓取課表：{target}")
            timetable = await self._crawler.fetch(target, refresh=kwargs.get('refresh', False))
            
            cached_result = CachedTimeTable(
                metadata=CacheMetadata(cache_fetch_at=datetime.now()),
                data=timetable
            )
            
            return cached_result
            
        except Exception as e:
            error_msg = f"從來源抓取課表失敗 {target}: {str(e)}"
            logger.warning(f"⚠️ {error_msg}")
            raise FetchError(error_msg)

    async def fetch(self, target: str, *, refresh: bool = False, **kwargs) -> CachedTimeTable:
        """智能獲取課表資料，自動處理三層快取
        
        Args:
            target: 目標名稱（班級或教師）
            refresh: 是否強制更新快取
            **kwargs: 傳遞給底層方法的額外參數
            
        Returns:
            CachedTimeTable: 完整的課表資料
        """
        result = await super().fetch(target=target, refresh=refresh, **kwargs)
        return result

@retry(
    stop=stop_after_attempt(2),  # 整體最多重試 2 次
    retry=retry_if_exception_type(FetchError),  # 只在獲取索引失敗時重試
    wait=wait_exponential(multiplier=1, min=1, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def preload_all(only_missing: bool = True, max_concurrent: int = 5, delay: float = 0.0):
    """預載入所有課表，加入併發上限與延遲控制
    
    Args:
        only_missing: 是否只載入缺少的課表，預設為 True
        max_concurrent: 最大併發請求數量，預設為 5
        delay: 每筆請求前的延遲秒數，預設為 0
    """
    from tnfsh_timetable_core import TNFSHTimetableCore
    import asyncio

    try:
        # 獲取索引
        core = TNFSHTimetableCore()
        index = await core.fetch_index(refresh=True)
        
        if not index.reverse_index:
            error_msg = "❌ 無法獲取課表索引"
            logger.error(error_msg)
            raise FetchError(error_msg)

        targets = index.get_all_targets()
        logger.info(f"🔄 開始預載入所有課表，共 {len(targets)} 項，延遲：{delay} 秒，併發上限：{max_concurrent}")

        cache = TimeTableCache()
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process(target: str):
            # 檢查是否已有快取
            if only_missing:
                cached = await cache.fetch_from_memory(target) or await cache.fetch_from_file(target)
                if cached:
                    logger.debug(f"⚡ 快取已存在，略過：{target}")
                    return
                
            # 內部重試函數
            @retry(
                stop=stop_after_attempt(3),  # 單個目標最多重試 3 次
                retry=retry_if_exception_type((
                    FetchError,
                    client_exceptions.ClientError,
                    client_exceptions.ServerTimeoutError,
                    asyncio.TimeoutError
                )),
                wait=wait_exponential(multiplier=1, min=1, max=5),
                before_sleep=before_sleep_log(logger, logging.DEBUG)
            )
            async def _fetch_with_retry():
                try:
                    async with semaphore:
                        if delay > 0:
                            await asyncio.sleep(delay)
                        await cache.fetch(target, refresh=True)
                        logger.debug(f"✅ 預載入成功：{target}")
                except Exception as e:
                    error_msg = f"預載入失敗 {target}: {str(e)}"
                    logger.warning(f"⚠️ {error_msg}")
                    raise FetchError(error_msg)
            
            try:
                await _fetch_with_retry()
            except Exception as e:
                logger.error(f"❌ {target} 重試耗盡仍然失敗: {str(e)}")

        # 並行處理所有目標
        await asyncio.gather(*(process(t) for t in targets))
        logger.info("🏁 預載入完成")

    except Exception as e:
        error_msg = f"預載入過程發生錯誤：{str(e)}"
        logger.error(f"❌ {error_msg}")
        raise FetchError(error_msg)

if __name__ == "__main__":
    import asyncio
    asyncio.run(preload_all(only_missing=False, max_concurrent=10, delay=0.0))
