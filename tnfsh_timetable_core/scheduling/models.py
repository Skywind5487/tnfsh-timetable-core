from __future__ import annotations
from math import log
import re
from typing import Dict, TYPE_CHECKING
from pydantic import BaseModel, RootModel
from tnfsh_timetable_core.timetable.models import CourseInfo
from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime
from tnfsh_timetable_core.utils.dict_like import dict_like

from tnfsh_timetable_core.scheduling.utils import is_free

# Global variables for caching
teacher_node_cache = {}
class_node_cache = {}

# === Forward reference：宣告在前、定義在後 ===
class CourseNode(BaseModel):
    time: StreakTime
    is_free: bool = False
    subject: str = ""
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
        result = f"<{t.weekday}-{t.period}(x{t.streak}) {'free' if self.is_free else 'busy'} T[{teacher_keys}] C[{class_keys}]>"
        result = f"{teacher_keys}[{t.period}]"
        return result

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


from tnfsh_timetable_core.abc.domain_abc import BaseDomainABC

if TYPE_CHECKING:
    from tnfsh_timetable_core.timetable.models import TimeTable
    from tnfsh_timetable_core.index.index import Index

class TeacherNodeDict(RootModel[
    Dict[str, TeacherNode]
], BaseDomainABC):

    @classmethod
    async def fetch(cls, *args, refresh: bool = False, **kwargs) -> TeacherNodeDict:
        """三層快取的統一入口，回傳 domain 實例
        此時 TeacherNode 尚未新增course
        """
        global teacher_node_cache
        if refresh:
            # 強制更新
            teacher_node_cache = {}
        if teacher_node_cache:
            # 如果快取中有資料，回傳新的實例
            return cls(root=teacher_node_cache)
        
        from tnfsh_timetable_core import TNFSHTimetableCore
        core = TNFSHTimetableCore()
        index:Index = await core.fetch_index()
        categories = index.index.teacher.data
        result: Dict[str, TeacherNode] = {}
        for category, items in categories.items():
            for teacher_name, url in items.items():
                if teacher_name not in result:
                    result[teacher_name] = TeacherNode(teacher_name=teacher_name, courses={})
        teacher_node_cache = result
        if result is None:
            print(f"Warning: {result} is None, this may be a problem.")
            raise ValueError("TeacherNodeDict fetch failed, result is None.")
        print(result)
        return cls(root=result)

class ClassNodeDict(RootModel[
    Dict[str, ClassNode]
], BaseDomainABC):

    @classmethod
    async def fetch(cls, *args, refresh: bool = False, **kwargs) -> ClassNodeDict:
        """三層快取的統一入口，回傳 domain 實例
        """
        global class_node_cache
        if refresh:
            # 強制更新
            class_node_cache = {}
        if class_node_cache:
            # 如果快取中有資料，回傳新的實例
            return cls(root=class_node_cache)
        
        from tnfsh_timetable_core import TNFSHTimetableCore
        core = TNFSHTimetableCore()
        index:Index = await core.fetch_index()
        categories = index.index.class_name.data
        result: Dict[str, ClassNode] = {}
        for category, items in categories.items():
            for class_name, url in items.items():
                if class_name not in result:
                    result[class_name] = ClassNode(class_name=class_name, courses={})
        class_node_cache = result
        return cls(root=result)
        

from tnfsh_timetable_core.timetable_slot_log_dict.timetable_slot_log_dict import TimetableSlotLogDict
async def build_course_node_from_log_dict(log_dict:TimetableSlotLogDict):
    """從課表時段紀錄字典建立課程節點"""
    from tnfsh_timetable_core.scheduling.models import CourseNode
    final_course_nodes_set = set()
    class_nodes: Dict[str, ClassNode] = await ClassNodeDict().fetch()
    teacher_nodes: Dict[str, TeacherNode] = await TeacherNodeDict().fetch()
    
    for (source, streak_time), course_info in log_dict.items():
        if source.isdigit():
            # 這是班級課程
            class_code = source
            if course_info is None:
                # 空堂
                course_node = CourseNode(
                    time=streak_time,
                    is_free=True,
                    subject="",
                    teachers={},
                    classes={class_code: class_nodes[class_code]}
                )
                final_course_nodes_set.add(course_node)
                continue
                
            # 處理有課程資訊的情況
            counter_parts = course_info.counterpart
            if len(counter_parts) != 1:
                # 多老師或多班級或無班級或無老師
                continue
            teacher_name = counter_parts[0].participant
            counter_log: CourseInfo = log_dict.get((teacher_name, streak_time))
            if counter_log is None:
                # 沒有對應的老師課程
                continue
            if len(counter_log.counterpart) != 1:
                # 多老師或多班級或無班級或無老師
                continue
            if counter_log.counterpart[0].participant != class_code:
                # 班級不對
                continue
            if counter_log.subject != course_info.subject:
                # 科目不對
                continue
            
            course_node = CourseNode(
                time=streak_time,
                is_free=False,
                subject=course_info.subject,
                teachers={teacher_name: teacher_nodes[teacher_name]},
                classes={class_code: class_nodes[class_code]}
            )
            final_course_nodes_set.add(course_node)
            
    # 更新所有節點的課程資訊
    for node in final_course_nodes_set:
        for teacher_name, teacher_node in node.teachers.items():
            if node.time not in teacher_node.courses:
                teacher_nodes[teacher_name].courses[node.time] = node
        for class_code, class_node in node.classes.items():
            if node.time not in class_node.courses:
                class_nodes[class_code].courses[node.time] = node


class NodeDicts:
    def __init__(self):
        self.teacher_nodes = None
        self.class_nodes = None
    
    async def fetch_teacher_nodes(self) -> TeacherNodeDict:
        if not self.teacher_nodes:
            self.teacher_nodes = await TeacherNodeDict.fetch()
        return self.teacher_nodes
    
    async def fetch_class_nodes(self) -> ClassNodeDict:
        if not self.class_nodes:
            self.class_nodes = await ClassNodeDict.fetch()
        return self.class_nodes

    async def fetch(self, log_dict: TimetableSlotLogDict = None) -> Dict[str, CourseNode]:        
        if log_dict is None:
            # 如果沒有提供 log_dict，則從快取獲取
            from tnfsh_timetable_core import TNFSHTimetableCore
            core = TNFSHTimetableCore()
            log_dict = await core.fetch_timetable_slot_log_dict()
        await self.fetch_teacher_nodes()
        await self.fetch_class_nodes()
        await build_course_node_from_log_dict(log_dict)

