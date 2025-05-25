from pydantic import BaseModel
from typing import Optional, TYPE_CHECKING

from functools import total_ordering
@total_ordering
class StreakTime(BaseModel):
    weekday: int
    period: int
    streak: int

    

    def __hash__(self):
        return hash((self.weekday, self.period))  # ✅ 只根據固定欄位 即使 streak 不同也能 get 到

    def __eq__(self, other):
        if not isinstance(other, StreakTime):
            return False
        return (
            self.weekday == other.weekday and
            self.period == other.period
        )
    
    def __lt__(self, other):
        if not isinstance(other, StreakTime):
            return NotImplemented
        return (self.weekday, self.period, self.streak) < (other.weekday, other.period, other.streak)




from tnfsh_timetable_core.timetable.models import CourseInfo

class TimetableSlotLog(BaseModel):
    source: str
    streak_time: StreakTime
    log: Optional["CourseInfo"]

TimetableSlotLog.model_rebuild()