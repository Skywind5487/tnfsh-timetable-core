from pydantic import BaseModel, RootModel
from typing import TypeAlias, Dict, Tuple, Optional
from tnfsh_timetable_core.utils.dict_like import dict_like
from tnfsh_timetable_core.abc.domain_abc import BaseDomainABC
from tnfsh_timetable_core.timetable_slot_log.models import StreakTime
from tnfsh_timetable_core.timetable.models import CourseInfo
from tnfsh_timetable_core.timetable_slot_log.cache import TimetableSlotLogCache

Source: TypeAlias = str
Log: TypeAlias = Optional[CourseInfo]

class TimetableSlotLog(BaseModel):
    source: str
    streak_time: StreakTime
    log: Log


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
    async def fetch(cls, cache: TimetableSlotLogCache = None) -> "TimetableSlotLogDict":
        """從快取獲取課表資料

        Args:
            cache: 快取實例。如果不提供，會建立新的 TimetableSlotLogCache

        Returns:
            TimetableSlotLogDict: 課表資料字典
        """
        if cache is None:
            cache = TimetableSlotLogCache()
        
        return await cache.fetch()
        

