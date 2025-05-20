import json
from typing import List, Optional, Dict, Tuple
from pathlib import Path
from tnfsh_timetable_core.abc.cache_abc import BaseCacheABC
from tnfsh_timetable_core.timetable_slot_log.timetable_slot_log import (
    TimetableSlotLog, 
    TimetableSlotLogDict,
    Source,
    Log
)
from tnfsh_timetable_core.timetable_slot_log.models import StreakTime
from tnfsh_timetable_core.timetable_slot_log.crawler import TimetableSlotLogCrawler

_memory_cache: Optional[TimetableSlotLogDict] = None

class TimetableSlotLogCache(BaseCacheABC):      
    def __init__(self, crawler: Optional[TimetableSlotLogCrawler] = None):
        """初始化 Cache

        Args:
            crawler: 課表資料爬蟲。如果不提供，會使用預設的 TimetableSlotLogCrawler
        """
        self._crawler = crawler or TimetableSlotLogCrawler()
        self._cache_dir = Path("cache")
        self._cache_file = self._cache_dir / "timetable_slot_log.json"
        self._cache_dir.mkdir(exist_ok=True)
        
    def _convert_to_dict(self, logs: List[TimetableSlotLog]) -> TimetableSlotLogDict:
        """將 List[TimetableSlotLog] 轉換為 TimetableSlotLogDict"""
        result: Dict[Tuple[Source, StreakTime], Log] = {}
        for log in logs:
            result[(log.source, log.streak_time)] = log.log
        return TimetableSlotLogDict(root=result)    
    
    async def fetch(self, refresh: bool = False) -> TimetableSlotLogDict:
        """統一對外取得資料，依序從 memory/file/source 取得"""
        if not refresh:
            # 嘗試從記憶體取得
            data = await self.fetch_from_memory()
            if data is not None:
                return data
            
            # 嘗試從檔案取得
            data = await self.fetch_from_file()
            if data is not None:
                await self.save_to_memory(data)
                return data
        
        # 從來源取得新資料
        logs = await self.fetch_from_source()
        data = self._convert_to_dict(logs)
        await self.save_to_memory(data)  # 記憶體存 TimetableSlotLogDict
        await self.save_to_file(logs)  # 檔案存成 List[TimetableSlotLog]
        return data    
    
    async def fetch_from_memory(self) -> Optional[TimetableSlotLogDict]:
        """從記憶體快取取得資料"""
        global _memory_cache
        return _memory_cache

    async def fetch_from_file(self) -> Optional[TimetableSlotLogDict]:
        """從本地檔案快取取得資料"""
        if not self._cache_file.exists():
            return None
        
        try:
            with open(self._cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                logs = [TimetableSlotLog(**item) for item in data]
                return self._convert_to_dict(logs)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    async def fetch_from_source(self) -> List[TimetableSlotLog]:
        """從爬蟲取得資料"""
        raw_data = await self._crawler.fetch_raw()
        return self._crawler.parse(raw_data)    
    
    async def save_to_memory(self, data: TimetableSlotLogDict) -> None:
        """儲存資料到記憶體快取"""
        global _memory_cache
        _memory_cache = data

    async def save_to_file(self, data: List[TimetableSlotLog]) -> None:
        """儲存資料到本地檔案快取，存成 List[TimetableSlotLog] 格式"""
        json_data = [item.model_dump() for item in data]
        with open(self._cache_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)