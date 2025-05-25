from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Optional, Generator

if TYPE_CHECKING:
    from tnfsh_timetable_core.scheduling.models import CourseNode


class Scheduling:
    async def rotation(self, teacher_name: str, weekday: int, period: int, max_depth: int = 3, refresh: bool = False) -> Generator[List[CourseNode], None, None]:
        """搜尋從指定老師的課程開始的所有可能輪調環路
        
        Args:
            teacher_name: 老師姓名
            weekday: 星期幾 (1-5)
            period: 第幾節課 (1-8)
            max_depth: 最大搜尋深度，預設為3
            refresh: 是否重新載入資料，預設為False

        Returns:
            Generator[List[CourseNode], None, None]: 生成所有找到的環路
        """
        course_node = await self.fetch_course_node(teacher_name, weekday, period, refresh=refresh)
        if not course_node:
            raise ValueError(f"課程節點不存在：{teacher_name} 在 {weekday} 星期 {period} 節")
        return self.origin_rotation(course_node, max_depth=max_depth)

    async def swap(self, teacher_name: str, weekday: int, period: int, max_depth: int = 3, refresh: bool = False):
        # fetch course node
        course_node = await self.fetch_course_node(teacher_name, weekday, period, refresh=refresh)
        if not course_node:
            raise ValueError(f"課程節點不存在：{teacher_name} 在 {weekday} 星期 {period} 節")

        return self.origin_swap(course_node, max_depth=max_depth)

    def origin_rotation(self, start: CourseNode, max_depth: int = 10) -> Generator[List[CourseNode], None, None]:
        from tnfsh_timetable_core.scheduling.rotation import rotation
        return rotation(start, max_depth=max_depth)

    def origin_swap(self, start: CourseNode, max_depth: int = 10) -> Generator[List[CourseNode], None, None]:
        from tnfsh_timetable_core.scheduling.swap import merge_paths
        return merge_paths(start, max_depth=max_depth)

    async def fetch_course_node(self, teacher_name: str, weekday: int, period: int, refresh: bool = False) -> CourseNode:
        """從教師名稱、星期幾和第幾節獲取課程節點"""
        from tnfsh_timetable_core.scheduling.models import NodeDicts
        from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime
        # Todo: streak要用算的
        streak_time = StreakTime(weekday=weekday, period=period, streak=1)
        node_dicts = await NodeDicts.fetch(refresh=refresh)

        if not node_dicts.teacher_nodes:
            raise ValueError("教師節點字典為空")
            
        teacher = node_dicts.teacher_nodes.root.get(teacher_name)
        if not teacher:
            available_teachers = list(node_dicts.teacher_nodes.root.keys())
            raise ValueError(f"找不到教師：{teacher_name}。可用的教師：{available_teachers}")
            
        course_node = teacher.courses.get(streak_time)
        if not course_node:
            raise ValueError(f"課程節點不存在：{teacher_name} 在 {streak_time}")
            
        return course_node