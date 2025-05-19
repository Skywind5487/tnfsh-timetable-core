from typing import Optional
from pathlib import Path
import json
import asyncio
from datetime import datetime
from tnfsh_timetable_core.index.models import IndexResult, AllTypeIndexResult
from tnfsh_timetable_core.index.crawler import request_all_index, merge_results, re
from tnfsh_timetable_core.utils.logger import get_logger

logger = get_logger(logger_level="INFO")

# 記憶體快取
_memory_cache: Optional[AllTypeIndexResult] = None

# 本地 JSON 快取目錄
CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

async def load_from_memory() -> Optional[AllTypeIndexResult]:
    """從記憶體載入快取的索引資料"""
    if _memory_cache is not None:
        logger.debug("✨ 從記憶體快取取得索引")
        return _memory_cache
    return None

async def save_to_memory(data: AllTypeIndexResult):
    """將索引資料儲存到記憶體快取"""
    global _memory_cache
    _memory_cache = data
    logger.debug("✨ 已更新記憶體快取")
    return _memory_cache

async def load_from_disk() -> Optional[AllTypeIndexResult]:
    """從磁碟載入快取的索引資料"""
    path = CACHE_DIR / "all_type_index.json"
    try:
        if path.exists() and path.stat().st_size > 0:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                result = AllTypeIndexResult.model_validate(data)
                # 更新記憶體快取
                await save_to_memory(result)
                logger.debug("💾 從檔案載入索引快取")
                return result
    except Exception as e:
        logger.error(f"讀取快取檔案時發生錯誤: {e}")
    return None

async def save_to_disk(data: AllTypeIndexResult):
    """將索引資料儲存到磁碟快取"""
    path = CACHE_DIR / "all_type_index.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(data.model_dump_json(indent=4))
            logger.debug("💾 已更新檔案快取")
    except Exception as e:
        logger.error(f"儲存快取檔案時發生錯誤: {e}")

async def fetch_with_cache(base_url: str, refresh: bool = False) -> AllTypeIndexResult:
    """支援三層快取的智能載入方法
    
    Args:
        base_url (str): 基礎 URL
        refresh (bool): 是否強制重新載入

    Returns:
        AllTypeIndexResult: 索引結果
    """
    if not refresh:
        # 1. 檢查記憶體快取
        if mem_cache := await load_from_memory():
            return mem_cache
        
        # 2. 檢查檔案快取
        if disk_cache := await load_from_disk():
            await save_to_memory(disk_cache)
            return disk_cache
    
    # 3. 從網路獲取
    from tnfsh_timetable_core.index.crawler import fetch_all_index
    logger.info(f"🌐 從網路抓取索引資料：{base_url}")
    all_index_result: AllTypeIndexResult = await fetch_all_index(base_url)

    # 更新快取
    await save_to_memory(all_index_result)
    await save_to_disk(all_index_result)

    return all_index_result

if __name__ == "__main__":
    # For test cases, see: tests/test_index/test_cache.py
    pass
