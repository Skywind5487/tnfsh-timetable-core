from pydantic import BaseModel
from tnfsh_timetable_core.timetable.models import CourseInfo

class StreakTime(BaseModel):
    weekday: int 
    period: int
    streak: int

class OriginLog(BaseModel):
    source: str # could be teacher or class_code
    time: StreakTime
    log: CourseInfo    