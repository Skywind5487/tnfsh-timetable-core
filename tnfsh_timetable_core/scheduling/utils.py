"""
提供共用的工具函式
"""
from asyncio import Condition
from typing import TYPE_CHECKING, List, Dict, Literal, Set, Optional
from __future__ import annotations
from warnings import deprecated
from xml.sax.handler import feature_external_ges

from tests.test_virtual_scheduling import src

if TYPE_CHECKING:
    from tnfsh_timetable_core.scheduling.models import CourseNode, ClassNode, TeacherNode
    from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime


@deprecated
def connect_neighbors(nodes: List[CourseNode]) -> None:
    """連接課程節點，使每個節點都成為其他節點的鄰居
    
    Args:
        nodes: 需要互相連接的課程節點列表
    """
    for course in nodes:
        course.neighbors = course.neighbors + [
            n for n in nodes 
            if (
                n is not course
                and not 
                n in course.neighbors
            )
        ]

def is_valid_course_node(course: CourseNode) -> bool:
    condition = (
        len(course.teachers) <= 1 and
        len(course.classes)  <= 1
    )
    return condition

def get_neighbors(course: CourseNode) -> List[CourseNode]:
    """取得課程節點的所有鄰居
    
    Args:
        course: 課程節點

    Returns:
        List[CourseNode]: 課程節點的所有鄰居
    """
    src_class = list(course.classes.values())[0]
    return list(src_class.courses.values()) # 取得所有課程節點

def is_free(course: Optional[CourseNode], mode: Literal["rotation", "swap"], freed: Optional[Set[CourseNode]]) -> bool:
    """檢查課程是否可用
    
    課程在以下情況被視為可用： 
    1. 課程標記為空堂（is_free=True）
    2. 課程已在當前路徑中被釋放（在 freed 集合中）
    
    Args:
        course: 要檢查的課程節點
        mode: 算法模式
        freed: 已被釋放的課程節點集合
        
    Returns:
        bool: 課程是否可用
    """
    if course in freed and mode == "swap":
        return True
    
    return course.is_free

def find_streak_start_if_free(course: CourseNode) -> Optional[CourseNode]:
    src_class = list(course.classes.values())[0]
    time = course.time
    for i in range(time.period, 1):
        candidate = src_class.courses.get(StreakTime(
            weekday=time.weekday,
            period=i,
            streak=time.streak
        ))
        if candidate and candidate.is_free:
            if candidate.streak >= (time.period - i) + time.streak:
                return candidate
            else:
                return None
    return None

def get_1_hop(
        src: CourseNode,
        dst: CourseNode,
        *,
        type: Literal["fwd", "bwd"],
        mode: Literal["rotation", "swap"],
        freed: Optional[Set[CourseNode]] = None
) -> Optional[CourseNode]:
    """檢查課程是否可用
    Condition:
    1. 找到頭且為空堂
        - 檢查 streak 是否足夠
    2. 找到頭且不為空堂
        - 檢查 streak 是否相同
    3. 找到中段且為空堂
        - 往前搜尋 streak 開始
        - 檢查 streak 是否足夠
    4. 找到中段且不為空堂
        - 不需要的情況
        
    Args:
        src: 源課程節點
        dst: 目標課程節點
        freed: 已釋放的課程節點集合
        
    Returns:
        Optional[CourseNode]: 可用的課程節點，若不存在則返回 None
    """
    # 取得 src 和 dst 的教師
    # 以 bwd 為主，若為 fwd 則交換
    if type == "fwd":
        src, dst = dst, src

    if freed is None:
        freed = set()

    src_teacher = src.teachers[0]
    dst_time = dst.time
    hop_1 = src_teacher.courses.get(dst_time, None)
    if hop_1:
        # 找到頭
        if is_free(hop_1, mode=mode, freed=freed):
            # 找到頭且為空堂
            if hop_1.streak >= dst_time.streak:
                return hop_1
            else:
                return None
        else:
            # 找到頭且不為空堂
            if hop_1.streak == dst_time.streak:
                return hop_1
            else:
                return None
    else:
        # 找到中段
        candidate = find_streak_start_if_free(src)
        if candidate:
            # 找到中段且為空堂
            if is_free(candidate, mode=mode, freed=freed):
                # 往前搜尋 streak 開始
                    return candidate
            else:
                # 找到中段且不為空堂
                return None
        else:
            # 找不到中段的頭 或 streak 不合
            return None
        