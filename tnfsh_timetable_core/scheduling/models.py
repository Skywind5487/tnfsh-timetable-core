from typing import Dict, TypeAlias, Tuple
from tnfsh_timetable_core.utils.dict_like import dict_like

from pydantic import BaseModel
from tnfsh_timetable_core.timetable.models import CourseInfo
from typing import Dict
from pydantic import BaseModel, RootModel


# === StreakTime：時間欄位，可當作 dict key ===
class StreakTime(BaseModel):
    weekday: int
    period: int
    streak: int

    def __hash__(self):
        return hash((self.weekday, self.period))  # ✅ 只根據固定欄位

    def __eq__(self, other):
        if not isinstance(other, StreakTime):
            return False
        return (
            self.weekday == other.weekday and
            self.period == other.period
        )

# === Forward reference：宣告在前、定義在後 ===
class CourseNode(BaseModel):
    time: StreakTime
    teachers: Dict[str, "TeacherNode"]
    classes: Dict[str, "ClassNode"]


class TeacherNode(BaseModel):
    teacher_name: str
    courses: Dict[StreakTime, "CourseNode"]


class ClassNode(BaseModel):
    class_code: str
    courses: Dict[StreakTime, "CourseNode"]


Source: TypeAlias = str
Log: TypeAlias = CourseInfo
# === OriginLog：用來記錄原始課表資料 ===
@dict_like
class OriginLog(RootModel[
    Dict[
        Tuple[Source, StreakTime], 
        Log
    ]]):
    pass

# ✅ 重建 forward reference（Pydantic 解析字串型別）
CourseNode.model_rebuild()
TeacherNode.model_rebuild()
ClassNode.model_rebuild()
