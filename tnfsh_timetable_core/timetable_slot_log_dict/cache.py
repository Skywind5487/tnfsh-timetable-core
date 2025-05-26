import json
from typing import List, Optional, Dict, Tuple, TYPE_CHECKING
from pathlib import Path
from venv import logger
from weakref import ref
from tnfsh_timetable_core.abc.cache_abc import BaseCacheABC
from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime, TimetableSlotLog

if TYPE_CHECKING:
    from tnfsh_timetable_core.timetable_slot_log_dict.timetable_slot_log_dict import TimetableSlotLogDict
    from tnfsh_timetable_core.timetable_slot_log_dict.crawler import TimetableSlotLogCrawler
    from tnfsh_timetable_core.timetable.models import CourseInfo

from tnfsh_timetable_core.utils.logger import get_logger
logger = get_logger(logger_level="DEBUG")

# 型別別名
Source = str
Log = Optional["CourseInfo"]

_memory_cache: Optional["TimetableSlotLogDict"] = None

class TimetableSlotLogCache(BaseCacheABC):        
    def __init__(self, crawler: Optional["TimetableSlotLogCrawler"] = None):
        """初始化 Cache

        Args:
            crawler: 課表資料爬蟲。如果不提供，會在需要時動態導入並建立 TimetableSlotLogCrawler
        """
        self._crawler = crawler
        if self._crawler is None:
            from tnfsh_timetable_core.timetable_slot_log_dict.crawler import TimetableSlotLogCrawler
            self._crawler = TimetableSlotLogCrawler()
            
        self._cache_dir = Path(__file__).resolve().parent / "cache"
        self._cache_file = self._cache_dir / "timetable_slot_log.json"
        self._cache_dir.mkdir(exist_ok=True)
    
    def _convert_to_dict(self, logs: List[TimetableSlotLog]) -> "TimetableSlotLogDict":
        """將 List[TimetableSlotLog] 轉換為 TimetableSlotLogDict"""
        # 動態引入，避免循環引用
        from tnfsh_timetable_core.timetable_slot_log_dict.timetable_slot_log_dict import TimetableSlotLogDict
        
        result: Dict[Tuple[str, StreakTime], Optional["CourseInfo"]] = {}
        for log in logs:
            result[(log.source, log.streak_time)] = log.log
        return TimetableSlotLogDict(root=result)
            
    async def fetch(self, refresh: bool = False) -> "TimetableSlotLogDict":
        """統一對外取得資料，依序從 memory/file/source 取得"""
        # 清除記憶體快取，如果要強制更新
        global _memory_cache
        if refresh:
            _memory_cache = None
        
        # 1. 檢查記憶體快取
        if mem := await self.fetch_from_memory():
            return mem
        
        # 2. 檢查檔案快取
        if (not refresh) and (disk := await self.fetch_from_file()):
            await self.save_to_memory(disk)
            return disk
            
        # 3. 從爬蟲取得資料
        logs = await self.fetch_from_source(refresh=refresh)
        logger.debug(f"從爬蟲取得 {len(logs)} 條課表時段紀錄")

        # 轉換並儲存到兩層快取
        data = self._convert_to_dict(logs)
        await self.save_to_memory(data)  # 記憶體存成 TimetableSlotLogDict
        await self.save_to_file(logs)  # 檔案存成 List[TimetableSlotLog]
        return data    
            
    async def fetch_from_memory(self) -> Optional["TimetableSlotLogDict"]:
        """從記憶體快取取得資料"""
        global _memory_cache
        return _memory_cache

    async def fetch_from_file(self) -> Optional["TimetableSlotLogDict"]:
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

    async def fetch_from_source(self, refresh: bool = False) -> List[TimetableSlotLog]:
        """從爬蟲取得資料"""
        return await self._crawler.fetch(refresh=refresh)    
            
    async def save_to_memory(self, data: "TimetableSlotLogDict") -> None:
        """儲存資料到記憶體快取"""
        global _memory_cache
        _memory_cache = data

    async def save_to_file(self, data: List[TimetableSlotLog]) -> None:
        """儲存資料到本地檔案快取，存成 List[TimetableSlotLog] 格式"""
        json_data = [item.model_dump() for item in data]
        with open(self._cache_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)