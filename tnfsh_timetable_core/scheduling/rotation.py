from __future__ import annotations

"""實作課程輪調的搜尋演算法"""
from typing import TYPE_CHECKING, List, Set, Optional, Generator
from tnfsh_timetable_core.scheduling.utils import connect_neighbors, get_1_hop, is_free, get_neighbors

if TYPE_CHECKING:
    from tnfsh_timetable_core.scheduling.models import TeacherNode, CourseNode
import logging
from typing import Generator, List, Set, Optional
from tnfsh_timetable_core.scheduling.models import CourseNode
from tnfsh_timetable_core.scheduling.utils import get_neighbors, get_1_hop, is_free
from tnfsh_timetable_core.utils.logger import get_logger

logger = get_logger(logger_level="DEBUG")

def rotation(start: CourseNode, max_depth: int = 10) -> Generator[List[CourseNode], None, None]:
    """深度優先搜尋環路的主函式
    
    Args:
        start: 起始課程節點
        max_depth: 最大搜尋深度，預設為10

    Returns:
        Generator[List[CourseNode], None, None]: 生成找到的所有環路，每個環路是一個 CourseNode 列表
    """
    
    def dfs_cycle(
        start: CourseNode,
        current: Optional[CourseNode] = None,
        depth: int = 0,
        path: Optional[List[CourseNode]] = None,
        visited: Optional[Set[CourseNode]] = None,
    ) -> Generator[List[CourseNode], None, None]:

        indent = "  " * depth

        if current is None:
            current = start
            logger.debug(f"\n🔍 開始 DFS | 深度: {depth}")
            logger.debug(f"{indent}🎯 起點: {start.short()}")
            path = [start]
            visited = set()

        if depth >= max_depth:
            logger.debug(f"{indent}⛔ 達到最大深度 {max_depth}，停止擴展")
            return

        for next_course in get_neighbors(current):
            logger.debug(f"\n{indent}➡️ 檢查相鄰課程: {next_course.short()}")
            logger.debug(f"{indent}↪️ 當前路徑 ({len(path)}): {' → '.join(n.short() for n in path)}")

            if next_course.time.period == 8:
                logger.debug(f"{indent}❌ 跳過 {next_course.short()} (第8節課程)")
                continue

            if is_free(next_course):
                logger.debug(f"{indent}✅ {next_course.short()} 是空堂不處理")
                continue
            
            if next_course == current:
                logger.debug(f"{indent}🔄 回到當前節點，跳過: {next_course.short()}")
                continue

            if next_course == start and depth > 0:
                complete_path = path + [start]
                logger.info(f"{indent}✅ 找到環路，長度 {len(complete_path)}")
                logger.info(f"{indent}🔄 路徑: {' → '.join(n.short() for n in complete_path)}")
                yield complete_path
                continue

            if next_course.time.streak != current.time.streak:
                logger.debug(f"{indent}❌ 不同streaks不可換課（{next_course.short()}與{current.short()}）")
                continue

            hop_1_bwd = get_1_hop(current, next_course, type="bwd")

            if not is_free(hop_1_bwd):
                logger.debug(f"{indent}❌ 非空堂不可換課（{hop_1_bwd.short() if hop_1_bwd else 'none'}）: {next_course.short()}")
                continue

            if next_course in visited:
                logger.debug(f"{indent}🔁 已訪問過，跳過: {next_course.short()}")
                continue

            visited.add(next_course)
            yield from dfs_cycle(start, next_course, depth + 1, path + [next_course], visited)
            visited.remove(next_course)


    yield from dfs_cycle(start)

