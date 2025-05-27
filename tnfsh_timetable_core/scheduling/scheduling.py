from __future__ import annotations
from ast import Await
from token import OP
from typing import TYPE_CHECKING, List, Set, Optional, Generator, Literal, Union


if TYPE_CHECKING:
    from tnfsh_timetable_core.scheduling.models import CourseNode
    from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime
    from tnfsh_timetable_core.scheduling.models import TeacherNode
    from tnfsh_timetable_core.scheduling.models import ClassNode


from tnfsh_timetable_core.utils.logger import get_logger
logger = get_logger(logger_level="DEBUG")

class Scheduling:
    async def rotation(self, teacher_name: str, weekday: int, period: int, max_depth: int = 3, refresh: bool = False) -> Generator[List[CourseNode], None, None]:
        """搜尋從指定老師的課程開始的所有可能輪調環路
        
        Args:
            teacher_name: 老師姓名
            weekday: 星期幾 (1-5)
            period: 第幾節課 (1-8)
            max_depth: 最大搜尋深度，預設為3。這裡指的是老師要移動幾次，必須大於1
            refresh: 是否重新載入資料，預設為False

        Returns:
            Generator[List[CourseNode], None, None]: 生成所有找到的環路
        """
        if max_depth <= 1:       
            raise ValueError("最大搜尋深度必須大於1")
        course_node = await self.fetch_course_node(teacher_name, weekday, period, refresh=refresh)
        if not course_node:
            raise ValueError(f"課程節點不存在：{teacher_name} 在 {weekday} 星期 {period} 節")
        return self._origin_rotation(course_node, max_depth=max_depth)

    async def swap(self, teacher_name: str, weekday: int, period: int, max_depth: int = 3, refresh: bool = False):
        """
        搜尋從指定老師的課程開始的所有可能互換路徑

        Args:
            teacher_name: 老師姓名
            weekday: 星期幾 (1-5)
            period: 第幾節課 (1-8)
            max_depth: 最大搜尋深度，預設為3。這裡指的是一組(兩個老師)要互換幾次，不須大於1，只需大於0
            refresh: 是否重新載入資料，預設為False

        Returns:
            Generator[List[CourseNode], None, None]: 生成所有找到的互換路徑
        """
        if max_depth <= 0:
            raise ValueError("最大搜尋深度必須大於0")
        course_node = await self.fetch_course_node(teacher_name, weekday, period, refresh=refresh)
        if not course_node:
            raise ValueError(f"課程節點不存在：{teacher_name} 在 {weekday} 星期 {period} 節")

        return self._origin_swap(course_node, max_depth=max_depth)

    def _origin_rotation(self, start: CourseNode, max_depth: int = 10) -> Generator[List[CourseNode], None, None]:
        from tnfsh_timetable_core.scheduling.rotation import rotation
        return rotation(start, max_depth=max_depth)

    def _origin_swap(self, start: CourseNode, max_depth: int = 10) -> Generator[List[CourseNode], None, None]:
        from tnfsh_timetable_core.scheduling.swap import merge_paths
        return merge_paths(start, max_depth=max_depth)

    async def fetch_course_node(self, teacher_name: str, weekday: int, period: int, refresh: bool = False) -> CourseNode:
        """從教師名稱、星期幾和第幾節獲取課程節點"""
        if not await self._check_course_valid(teacher_name, weekday, period, refresh=refresh):
            raise ValueError(f"無效的課程資訊：{teacher_name} 在 {weekday} 星期 {period} 節")
                
        from tnfsh_timetable_core.scheduling.models import NodeDicts
        from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime
        # Todo: streak要用算的
        streak_time = StreakTime(weekday=weekday, period=period, streak=1)
        node_dicts = await NodeDicts.fetch(refresh=refresh)

        if not node_dicts.teacher_nodes:
            raise ValueError("教師節點字典為空")
            
        teacher = node_dicts.teacher_nodes.root.get(teacher_name, None)
        if not teacher:
            available_teachers = list(node_dicts.teacher_nodes.root.keys())
            raise ValueError(f"找不到教師：{teacher_name}。可用的教師：{available_teachers}")
            
        course_node = self.find_streak_start(teacher, streak_time)
            
        return course_node
    
    def find_streak_start(self, node: Union[TeacherNode, ClassNode], streak_time: StreakTime) -> Optional[CourseNode]:
        """尋找課程的開始點"""
        time = streak_time
        courses = node.courses

        from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime

        for i in range(time.period, 0, -1):
            candidate = courses.get(StreakTime(
                weekday=time.weekday,
                period=i,
                streak=time.streak
            ))
    
            if candidate:    
                return candidate
    
        logger.debug(f"沒有找到開始點：{node.short()} 在 {streak_time}")

        return None
    
    async def _check_course_valid(self, teacher_name: str, weekday: int, period: int, refresh: bool = False) -> bool:
        from tnfsh_timetable_core import TNFSHTimetableCore
        core = TNFSHTimetableCore()
        table = await core.fetch_timetable(target=teacher_name, refresh=refresh)
        table = table.table
        from tnfsh_timetable_core.timetable.models import CourseInfo
        course_info: CourseInfo = table[weekday-1][period-1]
        if course_info is None:
            raise ValueError(f"{teacher_name}的星期{weekday}第{period}節是空堂，無法計算調課")
                
        # 處理有課程資訊的情況
        counter_parts = course_info.counterpart
        if not counter_parts:
            # 這節有課但沒參加的班級
            raise ValueError(f"{teacher_name}的星期{weekday}第{period}節沒有參加的班級")
        if len(counter_parts) != 1:
            # 多老師或多班級或無班級或無老師
            raise ValueError(f"{teacher_name}的星期{weekday}第{period}節有多個對應班級或老師，無法計算調課")
        
        return True
