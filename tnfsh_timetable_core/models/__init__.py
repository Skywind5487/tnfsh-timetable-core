# 統一 import 各 domain model
from tnfsh_timetable_core.timetable.models import TimeTable
from tnfsh_timetable_core.index.index import Index
from tnfsh_timetable_core.timetable_slot_log.timetable_slot_log import TimetableSlotLog

__all__ = [
    "TimeTable",
    "Index",
    "TimetableSlotLog",
]
# ...如有其他 domain model 也可在此加入...