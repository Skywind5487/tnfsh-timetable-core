from __future__ import annotations

from typing import TYPE_CHECKING, List, Dict, Literal, Set, Optional

from requests import get

if TYPE_CHECKING:
    from tnfsh_timetable_core.scheduling.models import CourseNode, ClassNode, TeacherNode
    from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime

from tnfsh_timetable_core.utils.logger import get_logger
logger = get_logger(logger_level="DEBUG")

# deprecated
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

def is_free(
        course: Optional[CourseNode], 
        mode: Literal["rotation", "swap"] = "rotation", 
        freed: Optional[Set[CourseNode]] = None
) -> bool:
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
    if (freed is not None) and course in freed and mode == "swap":
        pass
    if course is None:
        #print(course)
        return False
    return course.is_free

def find_streak_start_if_free(course: CourseNode) -> Optional[CourseNode]:
    src_class = list(course.classes.values())[0]
    print(f"尋找 {src_class.class_name} 的空堂開始點")
    if "陳婉玲" in course.teachers:
        # 陳婉玲的特殊處理
        print(f"陳婉玲的課程：{course}")
    time = course.time
    for i in range(time.period, 1):
        candidate = src_class.courses.get(StreakTime(
            weekday=time.weekday,
            period=i,
            streak=time.streak
        ))
        if candidate and candidate.is_free:
            if candidate.time.streak >= (time.period - i) + time.streak:
                return candidate
            else:
                return None
    return None

def get_1_hop(
        src: CourseNode,
        dst: CourseNode,
        *,
        type: Literal["fwd", "bwd"],
        mode: Literal["rotation", "swap"] = "rotation",
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
        Optional[CourseNode]: 可用的課程節點，可能是空堂或非空堂，若不存在則返回 None
    """
    # 取得 src 和 dst 的教師
    # 以 bwd 為主，若為 fwd 則交換
    if type == "fwd":
        src, dst = dst, src

    if freed is None:
        freed = set()

    src_teacher = list(src.teachers.values())[0]
    dst_time = dst.time
    src_courses = src_teacher.courses
    hop_1 = src_courses.get(dst_time, None)
    if hop_1 is None:
        # 沒有找到對應的課程節點
        logger.debug(f"Warning: {src_teacher.teacher_name}在 {dst_time} 找不到對應的課程節點")
        return None
    
    if hop_1:
        # 找到頭
        if "陳婉玲" in hop_1.teachers:
            print(f"陳婉玲的課程：{hop_1}")
        if is_free(hop_1, mode=mode, freed=freed):
            # 找到頭且為空堂
            if hop_1.time.streak >= dst_time.streak:
                return hop_1 
            else:
                # 找到頭但streak不足
                logger.debug(f"Warning: {src_teacher.teacher_name}在 {dst_time} 找到頭但streak不足")
                return None
        else:
            # 找到頭且不為空堂
            if hop_1.time.streak == dst_time.streak:
                return hop_1
            else:
                logger.debug(f"Warning: {src_teacher.teacher_name}在 {dst_time} 找到頭但不為空堂")
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
                logger.debug(f"Warning: {src_teacher.teacher_name}在 {dst_time} 找到中段但不為空堂")
                # 找到中段且不為空堂
                return None
        else:
            # 找不到中段的頭 或 streak 不合
            logger.debug(f"Warning: {src_teacher.teacher_name}在 {dst_time} 找不到中段的頭或streak不合")
            return None
        