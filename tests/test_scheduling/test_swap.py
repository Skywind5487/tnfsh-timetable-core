"""測試課程交換搜尋功能"""
from venv import logger
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


def test_single_swap_path():
    """測試簡單的單一交換路徑情境
    
    情境：
    - 建立兩位老師和三個班級
    - A老師：一節需交換課程(a1)，多節空堂(a2-a5)
    - B老師：多節空堂(b1,b3-b5)，一節交換課程(b2)
    - 班級安排：
      - 101班：a1和b2，用於交換的課程
      - 102班：a2-a5，用於提供A老師的空堂
      - 103班：b1,b3-b5，用於提供B老師的空堂
    
    結構：
    a1 需要與 b2 交換（同屬101班），有多個可能的空堂路徑，但應該選擇最短的路徑：
    a2_(空堂) -> a1 -> b2 -> b1_(空堂)
    
    檢查項目：
    1. 確保要交換的課程(a1,b2)在同一個班級
    2. 應該只找到一條最短路徑
    3. 路徑應該在找到第一個空堂時停止
    4. 不應該探索其他可能但更長的路徑
    """
    # === 建立老師與班級 ===
    teacher_A = TeacherNode(teacher_name="A", courses={})
    teacher_B = TeacherNode(teacher_name="B", courses={})
    
    # 建立班級
    cls_101 = ClassNode(class_code="101", courses={})  # 用於交換的班級，包含 a1 和 b2
    cls_102 = ClassNode(class_code="102", courses={})  # A老師空堂的班級
    cls_103 = ClassNode(class_code="103", courses={})  # B老師空堂的班級

    # === 建立課程節點 ===
    # A老師的課程
    a1 = build_course(teacher_A, cls_101, weekday=1, period=1, streak=1, is_free=False)  # 起點課程，需要交換
    a2 = build_course(teacher_A, cls_102, weekday=1, period=2, streak=1, is_free=True)   # A的空堂
    a3 = build_course(teacher_A, cls_102, weekday=1, period=3, streak=1, is_free=True)   # A的空堂
    a4 = build_course(teacher_A, cls_102, weekday=1, period=4, streak=1, is_free=True)   # A的空堂
    a5 = build_course(teacher_A, cls_102, weekday=1, period=5, streak=1, is_free=True)   # A的空堂

    # B老師的課程
    b1 = build_course(teacher_B, cls_103, weekday=1, period=1, streak=1, is_free=True)   # B的空堂
    b2 = build_course(teacher_B, cls_101, weekday=1, period=2, streak=1, is_free=False)  # 要和 a1 交換的課程（同屬101班）
    b3 = build_course(teacher_B, cls_103, weekday=1, period=3, streak=1, is_free=True)   # B的空堂
    b4 = build_course(teacher_B, cls_103, weekday=1, period=4, streak=1, is_free=True)   # B的空堂
    b5 = build_course(teacher_B, cls_103, weekday=1, period=5, streak=1, is_free=True)   # B的空堂

    # === 執行交換路徑搜尋 ===
    paths = list(scheduling.origin_swap(a1))

    # === 驗證 ===
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

    # 確認要交換的課程在同一個班級
    assert a1.classes == b2.classes, "要交換的課程必須在同一個班級"


def test_no_valid_path_in_long_chain():
    """測試長鏈路超出深度限制的情況
    
    情境：
    建立一個長的課程交換鏈，其中：
    - 有10位老師 (A-J)，每位老師 3-4 節課
    - 每個老師的課程都在不同班級
    - 課程連接方式：A1 -> B2 -> C3 -> D1 -> E2 -> F3 -> G1 -> H2 -> I3 -> J1
    - 第一位老師的第二節課和最後一位老師的第二節課是空堂
    
    結構特點：
    1. 鏈路太長，超出搜尋深度限制（設為5）
    2. 雖然起點和終點都有空堂可用，但路徑無法被找到
    
    檢查項目：
    1. 在深度限制下應該找不到任何路徑
    2. 確保程式不會因為搜尋太深而卡住
    """
    # === 建立老師與班級 ===
    teachers = {
        ch: TeacherNode(teacher_name=ch, courses={})
        for ch in "ABCDEFGHIJ"  # 10位老師
    }
    
    classes = {
        f"{i:03}": ClassNode(class_code=f"{i:03}", courses={})
        for i in range(101, 111)  # 10個班級
    }    # === 建立課程節點 ===
    courses = {}
    
    # 形成長鏈：A1 -> B2 -> C3 -> D1 -> E2 -> F3 -> G1 -> H2 -> I3 -> J1
    chain = ["A1", "B2", "C3", "D1", "E2", "F3", "G1", "H2", "I3", "J1"]

    # 為每位老師建立3節課，每兩個相鄰的課程共用一個班級以便交換
    for i, (teacher_name, teacher) in enumerate(teachers.items()):
        for j in range(1, 4):  # 1, 2, 3 節課
            course_id = f"{teacher_name}{j}"
            
            # 如果這個課程在鏈中，找出它的下一個課程
            next_course_id = None
            if course_id in chain:
                idx = chain.index(course_id)
                if idx < len(chain) - 1:
                    next_course_id = chain[idx + 1]
            
            # 決定使用哪個班級
            if next_course_id:
                # 如果課程在鏈中，使用與下一個課程相同的班級
                cls = classes[f"{101+i:03}"]
            else:
                # 如果不在鏈中，使用自己的班級
                cls = classes[f"{101+((i+j)%10):03}"]
            
            # 建立課程
            courses[course_id] = build_course(
                teacher, cls,
                weekday=1, period=j, streak=1,
                is_free=(course_id[0] in "AJ" and j == 2)  # A2和J2是空堂
            )

    # === 設定較小的深度限制並執行搜尋 ===
    paths = list(scheduling.origin_swap(courses["A1"], max_depth=5))


    # === 驗證 ===
    # 不應該找到任何路徑（因為超出深度限制）
    logger.debug(f"找到的路徑: {paths}")
    assert len(paths) == 0, f"預期找不到任何路徑（深度限制5），但找到了{len(paths)}條路徑"

    # 印出鏈路結構（用於除錯）
    logger.debug("=== 課程鏈路 ===")
    logger.debug(" → ".join(f"{node}{'_' if courses[node].is_free else ''}" for node in chain))