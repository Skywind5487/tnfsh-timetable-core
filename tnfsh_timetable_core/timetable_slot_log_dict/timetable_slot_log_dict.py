from sqlite3 import Time
from pydantic import RootModel
from typing import TypeAlias, Dict, Tuple, Optional, TYPE_CHECKING 
from tnfsh_timetable_core.utils.dict_like import dict_like
from tnfsh_timetable_core.abc.domain_abc import BaseDomainABC
from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime
from tnfsh_timetable_core.timetable.models import CourseInfo


if TYPE_CHECKING:
    from tnfsh_timetable_core.timetable_slot_log_dict.cache import TimetableSlotLogCache

Source: TypeAlias = str
Log: TypeAlias = Optional["CourseInfo"]

# === OriginLog：用來記錄原始課表資料 ===
@dict_like
class TimetableSlotLogDict(
    RootModel[
        Dict[
            Tuple[Source, StreakTime], 
            Log
        ]
    ],
    BaseDomainABC):
    
    @classmethod
    async def fetch(cls, cache: "TimetableSlotLogCache" = None, refresh: bool = False) -> "TimetableSlotLogDict":
        """從快取獲取課表資料

        Args:
            cache: 快取實例。如果不提供，會建立新的 TimetableSlotLogCache

        Returns:
            TimetableSlotLogDict: 課表資料字典
        """
        if cache is None:
            # 動態引入避免循環引用
            from tnfsh_timetable_core.timetable_slot_log_dict.cache import TimetableSlotLogCache
            cache = TimetableSlotLogCache()
        
        return await cache.fetch(refresh=refresh)

    @classmethod
    async def fetch_without_cache(cls):
        """取得最新資料（不使用快取）"""
        # 動態引入，避免循環引用
        from tnfsh_timetable_core.timetable_slot_log_dict.cache import TimetableSlotLogCache
        
        cache = TimetableSlotLogCache()
        return await cache.fetch(refresh=True)


