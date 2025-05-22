from typing import Dict, TypeAlias, Tuple
from tnfsh_timetable_core.utils.dict_like import dict_like

from pydantic import BaseModel
from tnfsh_timetable_core.timetable.models import CourseInfo
from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime
from typing import Dict
from pydantic import BaseModel, RootModel

from tnfsh_timetable_core.scheduling.utils import is_free

# === Forward reference：宣告在前、定義在後 ===
class CourseNode(BaseModel):
    time: StreakTime
    is_free: bool = False
    teachers: Dict[str, "TeacherNode"]
    classes: Dict[str, "ClassNode"]

    def __hash__(self) -> int:
        teacher_keys = tuple(sorted(self.teachers.keys()))
        class_keys = tuple(sorted(self.classes.keys()))
        return hash((self.time, teacher_keys, class_keys))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CourseNode):
            return NotImplemented
        return (self.time == other.time and
                self.is_free == other.is_free and
                self.teachers == other.teachers and
                self.classes == other.classes
                )
    
    def short(self) -> str:
        teacher_keys = ",".join(sorted(self.teachers))
        class_keys = ",".join(sorted(self.classes))
        t = self.time
        return f"<{t.weekday}-{t.period}(x{t.streak}) {'free' if self.is_free else 'busy'} T[{teacher_keys}] C[{class_keys}]>"

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
