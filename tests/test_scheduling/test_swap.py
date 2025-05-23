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


def test_no_valid_path_in_long_chain(n: int = 10):  # 改為預設10位老師
    """測試長鏈路超出路徑長度限制的情況
    
    描述：
    建立一個長的課程交換鏈，其中：
    1. 有 n 位老師（預設15位）
    2. 每位老師的課程分布：
       - 第1節：作為 fwd_hop 使用，非空堂
       - 第2-4節：根據交換鏈配置
    3. 課程連接方式（以前4個老師為例）：
       A[1] -> B[3]：
           - 使用 class_1 連接 A[1] 和 B[3]
           - fwd：B[1] 在 class_1（B老師第1節，和A[1]同班）
           - bwd：A[3]（A老師第3節，空堂）
       B[1] -> C[4]：
           - 使用 class_2 連接 B[1] 和 C[4]
           - fwd：C[1] 在 class_2（C老師第1節，和B[1]同班）
           - bwd：B[4]（B老師第4節，空堂）
       C[1] -> D[2]：
           - 使用 class_3 連接 C[1] 和 D[2]
           - fwd：D[1] 在 class_3（D老師第1節，和C[1]同班）
           - bwd：C[2]（C老師第2節，空堂）
    
    規則：
    1. 每個老師的第1節課作為 fwd_hop，必須是非空堂
    2. 每對需要交換的課程都在同一個班級
    3. 每個老師都有一節課是空堂，用於 bwd_hop
    
    預期：
    - 由於路徑長度超過限制（設為5），不會找到任何路徑
    """
    # === 建立老師、班級、交換規則 ===
    teacher_names = "ABCDEFGHIJ"[:n]  # 最多10位老師
    teachers = {
        ch: TeacherNode(teacher_name=ch, courses={})
        for ch in teacher_names
    }
    
    classes = {
        f"class_{i}": ClassNode(class_code=f"class_{i}", courses={})
        for i in range(1, n)  # n-1個班級，因為最後一個老師不需要往下連
    }
    
    # 建立交換鏈規則：[(老師, 時段), ...]
    # 例如：[('A', 3), ('B', 4), ('C', 2)] 表示 A[1]->B[3], B[1]->C[4], C[1]->D[2]
    exchange_chain = []
    for i in range(len(teacher_names)-1):  # 修改為使用 teacher_names 的長度
        src_teacher = teacher_names[i]
        dst_teacher = teacher_names[i+1]
        dst_period = (i % 3) + 2  # 2, 3, 4 循環
        exchange_chain.append((src_teacher, dst_period))
    
    # === 建立課程節點 ===
    courses = {}  # 儲存所有課程的字典：{課程ID: 課程節點}
    
    # 建立臨時班級，用於初始化課程
    temp_class = ClassNode(class_code="temp", courses={})
    
    for idx, (t_name, teacher) in enumerate(teachers.items()):
        for period in range(1, 5):  # 1-4節課
            # 決定這個課程是否為空堂
            is_free = False
            
            # 如果這是某個老師的 bwd_hop（和 dst 同時段，和 src 同老師）
            if idx < len(exchange_chain):  # 跳過最後一個老師
                _, dst_period = exchange_chain[idx]
                if period == dst_period:  # 如果時段符合
                    is_free = True
            
            # 建立課程節點
            course_id = f"{t_name}{period}"
            courses[course_id] = build_course(
                teacher=teacher,
                cls=temp_class,  # 使用臨時班級
                weekday=1,
                period=period,
                streak=1,
                is_free=is_free
            )
    
    # 清除所有課程的臨時班級關係
    for course in courses.values():
        course.classes.clear()
        if course.time in temp_class.courses:
            del temp_class.courses[course.time]
    
    # === 建立課程連接（通過加入同一班級） ===
    for idx, (src_teacher, dst_period) in enumerate(exchange_chain):
        dst_teacher = teacher_names[idx+1]
        cls = classes[f"class_{idx+1}"]
        
        # 1. src老師的第1節和dst老師的第dst_period節同班
        src_course = courses[f"{src_teacher}1"]
        dst_course = courses[f"{dst_teacher}{dst_period}"]
        
        # 將課程加入班級
        time_src = StreakTime(weekday=1, period=src_course.time.period, streak=1)
        time_dst = StreakTime(weekday=1, period=dst_course.time.period, streak=1)
        
        cls.courses[time_src] = src_course
        cls.courses[time_dst] = dst_course
        src_course.classes[cls.class_code] = cls
        dst_course.classes[cls.class_code] = cls
        
        
    
    # 印出課程結構（用於除錯）
    print("\n=== 課程結構 ===")
    for src_teacher, dst_period in exchange_chain:
        dst_teacher = teacher_names["ABCDEFGHIJ".index(src_teacher)+1]
        src_course = courses[f"{src_teacher}1"]
        dst_course = courses[f"{dst_teacher}{dst_period}"]
        fwd_course = courses[f"{dst_teacher}1"]
        
        print(f"\n交換對：{src_course.short()} -> {dst_course.short()}")
        print(f"- src課程：{src_course.short()} (第{src_course.time.period}節)")
        print(f"- dst課程：{dst_course.short()} (第{dst_course.time.period}節)")
        print(f"- fwd課程：{fwd_course.short()} (第{fwd_course.time.period}節)")
        print(f"- 共同班級：{list(src_course.classes.keys())}")
    
    # === 執行搜尋（深度限制=5）===
    start_course = courses["A1"]
    paths = list(scheduling.origin_swap(start_course, max_depth=5))
    
    # === 驗證結果 ===
    # 1. 不應該找到任何路徑（因為超出深度限制）
    assert len(paths) == 0, f"預期找不到任何路徑（深度限制5），但找到了{len(paths)}條路徑"
    
