"""測試課程交換搜尋功能"""
import pytest
from tnfsh_timetable_core.scheduling.models import CourseNode, TeacherNode, ClassNode
from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime
from tnfsh_timetable_core import TNFSHTimetableCore
from tnfsh_timetable_core.scheduling.utils import get_1_hop, is_free


def build_course(
    teacher: TeacherNode,
    cls: ClassNode,
    weekday: int,
    period: int,
    streak: int,
    is_free: bool = False
) -> CourseNode:
    """建立一個課程節點
    
    Args:
        teacher: 教師節點
        cls: 班級節點
        weekday: 星期幾 (1-5)
        period: 第幾節 (1-8)
        streak: 連續幾節課
        is_free: 是否為空堂
    """
    time = StreakTime(weekday=weekday, period=period, streak=streak)
    node = CourseNode(
        time=time,
        is_free=is_free,
        teachers={teacher.teacher_name: teacher},
        classes={cls.class_code: cls},
    )
    teacher.courses[time] = node
    cls.courses[time] = node
    return node


# 建立一個全域的 Scheduling 實例
core = TNFSHTimetableCore()
scheduling = core.get_scheduling()


def test_basic_path_stops_at_first_free():
    """測試基本路徑尋找功能：路徑應在找到第一個空堂時停止
    
    情境：最簡單的交換情況，建立兩個課程之間的交換
    - 建立兩位老師和兩個班級
    - A老師：一節非空堂(a1)和一節空堂(a2)
    - B老師：一節空堂(b1)和一節非空堂(b2)
    - 班級安排：
      - 101班：a1和b2，用於形成交換
      - 102班：a2，用於提供空堂
      - 103班：b1，用於提供空堂
    
    預期：
    1. 應找到一條路徑：a2_ -> a1 -> b2 -> b1_
    2. 路徑應在第一個空堂 (b1_) 結束
    """
    # === 建立老師與班級 ===
    teacher_A = TeacherNode(teacher_name="A", courses={})
    teacher_B = TeacherNode(teacher_name="B", courses={})
    cls_101 = ClassNode(class_code="101", courses={})  # 交換課程的班級
    cls_102 = ClassNode(class_code="102", courses={})  # A老師空堂的班級
    cls_103 = ClassNode(class_code="103", courses={})  # B老師空堂的班級

    # === 建立課程節點 ===
    # A老師的課程
    a1 = build_course(teacher_A, cls_101, weekday=1, period=1, streak=1, is_free=False)  # 起點課程（需要交換）
    a2 = build_course(teacher_A, cls_102, weekday=1, period=2, streak=1, is_free=True)   # A的空堂

    # B老師的課程
    b1 = build_course(teacher_B, cls_103, weekday=1, period=1, streak=1, is_free=True)   # B的空堂（預期終點）
    b2 = build_course(teacher_B, cls_101, weekday=1, period=2, streak=1, is_free=False)  # 要和 a1 交換的課程

    # === 執行交換路徑搜尋 ===
    paths = list(scheduling.origin_swap(a1))    # === 驗證 ===
    # 應該只找到一條路徑
    assert len(paths) == 1, f"預期找到1條路徑，實際找到{len(paths)}條"

    # 找到的路徑應該是：a2_ -> a1 -> b2 -> b1_
    expected_path = [a2, a1, b2, b1]
    actual_path = paths[0]
    
    # 印出實際找到的路徑
    print("\n=== 找到的路徑 ===")
    print(" → ".join(node.short() for node in actual_path))
    
    # 檢查路徑是否正確
    assert len(actual_path) == len(expected_path), f"路徑長度不符，預期{len(expected_path)}，實際{len(actual_path)}"
    for expected, actual in zip(expected_path, actual_path):
        assert expected == actual, f"路徑節點不符，預期{expected.short()}，實際{actual.short()}"

    # 確認路徑結尾是空堂
    assert actual_path[-1].is_free, "路徑應該在空堂結束"


def test_isolated_courses_have_no_path():
    """測試孤立課程節點的情況
    
    情境：
    - 建立兩個完全沒有連接的課程
    - 每個課程屬於不同的老師和班級
    - 課程之間沒有任何可能的交換方式
    
    檢查項目：
    1. 確認無法找到任何交換路徑
    2. swap.merge_paths 函數應該返回空列表
    """
    # === 建立老師與班級 ===
    teacher_A = TeacherNode(teacher_name="A", courses={})
    teacher_B = TeacherNode(teacher_name="B", courses={})
    cls_101 = ClassNode(class_code="101", courses={})
    cls_102 = ClassNode(class_code="102", courses={})

    # === 建立課程節點 ===
    a1 = build_course(teacher_A, cls_101, weekday=1, period=1, streak=1, is_free=False)
    b2 = build_course(teacher_B, cls_102, weekday=1, period=2, streak=1, is_free=False)

    # === 執行交換路徑搜尋 ===
    paths = list(scheduling.origin_swap(a1))

    # === 驗證：不應該找到任何路徑 ===
    assert len(paths) == 0, "孤立的課程節點不應該找到任何交換路徑"

    # === 額外驗證：確保課程確實是孤立的 ===
    # 檢查老師的課程
    assert len(teacher_A.courses) == 1 and a1 in teacher_A.courses.values(), "課程應該正確關聯到老師 A"
    assert len(teacher_B.courses) == 1 and b2 in teacher_B.courses.values(), "課程應該正確關聯到老師 B"
    
    # 檢查班級的課程
    assert len(cls_101.courses) == 1 and a1 in cls_101.courses.values(), "課程應該正確關聯到班級 101"
    assert len(cls_102.courses) == 1 and b2 in cls_102.courses.values(), "課程應該正確關聯到班級 102"