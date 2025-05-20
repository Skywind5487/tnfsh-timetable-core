from pydantic import RootModel
from typing import TypeAlias, Dict, Tuple
from tnfsh_timetable_core.utils.dict_like import dict_like
from tnfsh_timetable_core.models.domain_abc import BaseDomainABC
from tnfsh_timetable_core.timetable_slot_log.models import StreakTime

Source: TypeAlias = str
Log: TypeAlias = CourseInfo
# === OriginLog：用來記錄原始課表資料 ===
@dict_like
class TimetableSlotLog(
    RootModel[
        Dict[
            Tuple[Source, StreakTime], 
            Log
        ]
    ],
    BaseDomainABC):
    pass