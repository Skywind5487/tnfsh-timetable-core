from typing import Dict, TypeAlias, Tuple
from tnfsh_timetable_core.utils.dict_like import dict_like

from pydantic import BaseModel
from tnfsh_timetable_core.timetable.models import CourseInfo
from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime
from typing import Dict
from pydantic import BaseModel, RootModel

from tnfsh_timetable_core.scheduling.utils import is_free



# === StreakTime：時間欄位，可當作 dict key ===


# === Forward reference：宣告在前、定義在後 ===
class CourseNode(BaseModel):
    time: StreakTime
    is_free: bool = False
    teachers: Dict[str, "TeacherNode"]
    classes: Dict[str, "ClassNode"]


class TeacherNode(BaseModel):
    teacher_name: str
    courses: Dict[StreakTime, "CourseNode"]


class ClassNode(BaseModel):
    class_code: str
    courses: Dict[StreakTime, "CourseNode"]




# ✅ 重建 forward reference（Pydantic 解析字串型別）
CourseNode.model_rebuild()
TeacherNode.model_rebuild()
ClassNode.model_rebuild()
