"""課程交換的 DFS 搜尋實作"""
from typing import Generator, List, Set
from tnfsh_timetable_core.scheduling.models import TeacherNode, CourseNode
from tnfsh_timetable_core.scheduling.utils import (
    connect_neighbors,
    get_1_hop,
    get_neighbors,
    is_free
)
from tnfsh_timetable_core.utils.logger import get_logger

logger = get_logger(logger_level="DEBUG")

def merge_paths(start: CourseNode, max_depth: int=20) -> Generator[List[CourseNode], None, None]:
    """產生完整的交換路徑
    
    搜尋策略：
    1. 對每個相鄰節點，檢查前向和後向路徑
    2. 若找到合法路徑，將前向和後向路徑拼接
    3. 路徑必須以空堂結束
    
    Args:
        start: 起始課程節點
        
    Yields:
        List[CourseNode]: 完整的交換路徑（後向路徑 + 起點 + 前向路徑）
    """
    def _dfs_swap_path(
        start: CourseNode,
        current: CourseNode | None = None,
        *,
        depth: int = 0,
        path: List[CourseNode] | None = None,
    ) -> Generator[List[CourseNode], None, None]:
        """深度優先搜尋可行的交換路徑
        
        搜尋規則：
        1. 路徑上的節點視為已釋放（freed）
        2. 遇到空堂時產生一個路徑
        3. 每次移動需檢查前向和後向的可行性
        
        Args:
            start: 起始課程節點
            current: 當前課程節點
            depth: 當前搜尋深度
            path: 當前路徑
            
        Yields:
            List[CourseNode]: 找到的合法交換路徑
        """
        indent = "  " * depth
        logger.debug(f"\n{indent}=== DFS | 深度: {depth} ===")
        logger.debug(f"{indent}🔍 當前節點: {current.short() if current else start.short()}")
        if path:
            logger.debug(f"{indent}↪️ 當前路徑 ({len(path)}): {' → '.join(c.short() for c in path)}")

        if path is None:
            path = []
        if current is None:
            current = start

        if depth >= max_depth:
            logger.debug(f"{indent}⛔ 達到最大深度 {max_depth}，停止搜尋")
            return

        if current.is_free:
            result = path + [current]
            logger.info(f"{indent}✅ 找到空堂！產生路徑: {' → '.join(c.short() for c in result)}")
            yield result
            return

        freed: Set[CourseNode] = set(path)
        for next_node in get_neighbors(current):
            logger.debug(f"{indent}➡️ 檢查相鄰節點: {next_node.short()}")
            logger.debug(f"{indent}↪️ 當前路徑 ({len(path)}): {' → '.join(c.short() for c in path)}")
            if next_node.time.period == 8:
                logger.debug(f"{indent}❌ 跳過 {next_node.short()} (第8節課程)")
                continue
            if next_node.time.streak != current.time.streak:
                logger.debug(f"{indent}❌ 跳過 {next_node.short()} (streak不匹配: {next_node.time.streak} != {current.time.streak})")
                continue

            if next_node == current:
                logger.debug(f"{indent}🔄 跳過 {next_node.short()} (當前節點)")
                continue

            if next_node == start:
                logger.debug(f"{indent}🔄 跳過 {next_node.short()} (起點)")
                continue

            bwd_hop = get_1_hop(current, next_node, type="bwd", mode="swap", freed=freed)

            if not is_free(bwd_hop, mode="swap", freed=freed):
                logger.debug(f"{indent}❌ 跳過 {next_node.short()} (後向檢查{bwd_hop.short() if bwd_hop else 'None'}失敗)")
                continue

            fwd_hop = get_1_hop(current, next_node, type="fwd", mode="swap", freed=freed)
            logger.debug(f"{indent}➡️ 前向課程: {fwd_hop.short() if fwd_hop else 'None'}")
            
            if fwd_hop is None or fwd_hop == start:
                logger.debug(f"{indent}❌ 跳過（前向課程{fwd_hop.short() if fwd_hop else 'None'}無效）")
                continue

            if is_free(fwd_hop, mode="swap", freed=freed):
                result = path + [current, next_node, fwd_hop]
                logger.info(f"{indent}✅ 產生路徑: {' → '.join(c.short() for c in result)}")
                yield result
            else:
                logger.debug(f"{indent}🔍 繼續搜尋（從 {fwd_hop.short()} 開始）")
                yield from _dfs_swap_path(
                    start, fwd_hop, 
                    depth=depth + 1, 
                    path=path + [current, next_node]
                )

    logger.debug(f"\n========= 搜尋交換路徑 =========")
    logger.debug(f"🎯 起點課程: {start.short()}")

    for course in get_neighbors(start):
        logger.debug(f"\n➡️ 檢查相鄰課程: {course.short()}")

        if course.time.period == 8:
            logger.debug(f"❌ 跳過 {course.short()} (第8節課程)")
            continue

        if course.time.streak != start.time.streak:
            logger.debug(f"❌ 跳過（streak不匹配: {course.time.streak} != {start.time.streak}）")
            continue

        if course == start:
            logger.debug("🔄 跳過（當前節點）")
            continue        

        fwd_hop = get_1_hop(start, course, type="fwd")
        bwd_hop = get_1_hop(start, course, type="bwd")

        logger.debug(f"➡️ 前向課程: {fwd_hop.short() if fwd_hop else 'None'}")
        logger.debug(f"⬅️ 後向課程: {bwd_hop.short() if bwd_hop else 'None'}")
        
        if fwd_hop is None or fwd_hop == start or bwd_hop is None:
            logger.debug(f"❌ 跳過{fwd_hop.short() if fwd_hop else 'None'}（無效的前向或後向課程）")
            continue

        logger.debug("\n=== 搜尋後向路徑 ===")
        if is_free(bwd_hop):
            bwd_slices = [[bwd_hop]]
            logger.debug("✅ 後向路徑可直接使用")
        else:
            logger.debug("🔍 開始後向深度搜尋...")
            bwd_slices = list(_dfs_swap_path(start, bwd_hop))

        logger.debug("\n=== 搜尋前向路徑 ===")
        if is_free(fwd_hop):
            fwd_slices = [[course, fwd_hop]]
            logger.debug("✅ 前向路徑是空堂")
        else:
            logger.debug("🔍 開始前向深度搜尋...")
            fwd_slices = list(_dfs_swap_path(start, fwd_hop, path=[course]))

        logger.debug("\n=== 合併路徑 ===")
        for fwd in fwd_slices:
            for bwd in bwd_slices:
                complete_path = list(reversed(bwd)) + [start] + fwd
                logger.info(f"✅ 完整路徑: {' → '.join(c.short() for c in complete_path)}")
                yield complete_path

