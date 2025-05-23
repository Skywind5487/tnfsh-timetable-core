
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Optional, Generator
if TYPE_CHECKING:
    from tnfsh_timetable_core.scheduling.models import CourseNode


class Scheduling:
    def fetch_course_node(self, teacher_name: str, weekday: int, period: int):
        pass

    def rotation(self, teacher_name: str, weekday: int, period: int, max_depth: int = 3):
        # fetch course node
        pass

    def swap(self, teacher_name: str, weekday: int, period: int, max_depth: int = 3):
        # fetch course node
        pass

    def origin_rotation(self, start: CourseNode, max_depth: int = 3) -> Generator[List[CourseNode], None, None]:
        from tnfsh_timetable_core.scheduling.rotation import rotation
        return rotation(start, max_depth=max_depth)

    def origin_swap(self, start: CourseNode, max_depth: int = 3) -> Generator[List[CourseNode], None, None]:
        from tnfsh_timetable_core.scheduling.swap import merge_paths
        return merge_paths(start, max_depth=max_depth)