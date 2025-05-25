import pytest
import pytest_asyncio
from tnfsh_timetable_core.scheduling.models import CourseNode, TeacherNode, ClassNode
from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime
from tnfsh_timetable_core import TNFSHTimetableCore
from tnfsh_timetable_core.scheduling.utils import get_1_hop, is_free

from tnfsh_timetable_core import TNFSHTimetableCore


def build_course(
    teacher: TeacherNode,
    cls: ClassNode,
    weekday: int,
    period: int,
    streak: int,
    is_free: bool = False
) -> CourseNode:
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
scheduling = core.fetch_scheduling()


def test_simplest_rotation_path():
    """測試基本的輪調環路搜尋功能
    
    情境：
    - 建立兩個老師和三個班級
    - A老師：一節非空堂(a1)和一節空堂(a2)
    - B老師：一節空堂(b1)和一節非空堂(b2)
    - 班級安排：
      - 101班：a1和b2，用於形成環路
      - 102班：a2
      - 103班：b1
    """
    # === 建立老師與班級 ===
    teacher_A = TeacherNode(teacher_name="A", courses={})
    teacher_B = TeacherNode(teacher_name="B", courses={})
    cls = ClassNode(class_code="101", courses={})
    cls2 = ClassNode(class_code="102", courses={})
    cls3 = ClassNode(class_code="103", courses={})

    # === 建立課程節點 ===
    # 時間設為同一天不同節
    a1 = build_course(teacher_A, cls, weekday=1, period=1, streak=1, is_free=False)  # 起點
    a2 = build_course(teacher_A, cls2, weekday=1, period=2, streak=1, is_free=True)   # A 空堂
    b1 = build_course(teacher_B, cls3, weekday=1, period=1, streak=1, is_free=True)   # B 空堂
    b2 = build_course(teacher_B, cls, weekday=1, period=2, streak=1, is_free=False)  # 中繼點

    # === 由班級課程自動構成 neighbors ===
    # 現在 rotation 中會使用 get_neighbors()，會從 cls.courses.values() 推出全部節點
    # 所以不再需要手動 connect_neighbors

    # === 執行 rotation ===
    paths = list(scheduling.origin_rotation(a1, max_depth=5))

    # === 驗證：找到一條以自己結尾的環路 ===
    assert len(paths) >= 1
    found = False
    for path in paths:
        if path[0] == a1 and path[-1] == a1:
            found = True
    assert found, "應該找到一條從 a1 出發、以 a1 結尾的環路"


def test_no_cycle_when_teacher_busy():
    """測試當老師沒有空堂時無法形成輪調環路
    
    情境：
    - 建立一個四節課的輪調環路 a1 -> b2 -> c3 -> d4 -> a1
    - 將課程安排在同一個班級中的不同節次
    - A老師的課程安排：
      - a1 (第一節，要輪調)
      - a2 (第二節，非空堂，阻止 a1 -> b2 的移動)
      - a3 (第三節，空堂)
      - a4 (第四節，空堂)
    - 其他老師類似配置 
    """
    # === 建立老師 ===
    teacher_A = TeacherNode(teacher_name="A", courses={})
    teacher_B = TeacherNode(teacher_name="B", courses={})
    teacher_C = TeacherNode(teacher_name="C", courses={})
    teacher_D = TeacherNode(teacher_name="D", courses={})
      # === 建立班級 ===
    # 環路課程在同一個班級
    cls_101 = ClassNode(class_code="101", courses={})  # 環路課程的班級
    cls_102 = ClassNode(class_code="102", courses={})  # A老師其他課程的班級
    cls_103 = ClassNode(class_code="103", courses={})  # B老師其他課程的班級
    cls_104 = ClassNode(class_code="104", courses={})  # C老師其他課程的班級
    cls_105 = ClassNode(class_code="105", courses={})  # D老師其他課程的班級

    # === 建立課程節點 ===
    # A老師的課程
    a1 = build_course(teacher_A, cls_101, weekday=1, period=1, streak=1, is_free=False)  # 要輪調的課程（在環路中）
    a2 = build_course(teacher_A, cls_102, weekday=1, period=2, streak=1, is_free=False)  # 非空堂，阻止輪調
    a3 = build_course(teacher_A, cls_102, weekday=1, period=3, streak=1, is_free=True)
    a4 = build_course(teacher_A, cls_102, weekday=1, period=4, streak=1, is_free=True)
    
    # B老師的課程
    b1 = build_course(teacher_B, cls_103, weekday=1, period=1, streak=1, is_free=True)
    b2 = build_course(teacher_B, cls_101, weekday=1, period=2, streak=1, is_free=False)  # 要和 a1 交換的課程（在環路中）
    b3 = build_course(teacher_B, cls_103, weekday=1, period=3, streak=1, is_free=True)
    b4 = build_course(teacher_B, cls_103, weekday=1, period=4, streak=1, is_free=True)
    
    # C老師的課程 
    c1 = build_course(teacher_C, cls_104, weekday=1, period=1, streak=1, is_free=True)
    c2 = build_course(teacher_C, cls_104, weekday=1, period=2, streak=1, is_free=True)
    c3 = build_course(teacher_C, cls_101, weekday=1, period=3, streak=1, is_free=False)  # 要和 b2 交換的課程（在環路中）
    c4 = build_course(teacher_C, cls_104, weekday=1, period=4, streak=1, is_free=True)
    
    # D老師的課程
    d1 = build_course(teacher_D, cls_105, weekday=1, period=1, streak=1, is_free=True)
    d2 = build_course(teacher_D, cls_105, weekday=1, period=2, streak=1, is_free=True)
    d3 = build_course(teacher_D, cls_105, weekday=1, period=3, streak=1, is_free=True)
    d4 = build_course(teacher_D, cls_101, weekday=1, period=4, streak=1, is_free=False)  # 要和 c3 交換的課程（在環路中）
    
    # === 第一階段：檢查 bwd_check 的行為 ===
    # 手動檢查 a1 -> b2 的移動是否被阻止（因為 A2 非空堂）
    hop_1_bwd = get_1_hop(a1, b2, type="bwd")
    assert not is_free(hop_1_bwd), "A2 非空堂時，is_free 應該返回 False"    # === 第二階段：執行 rotation 並檢查結果 ===
    paths = list(scheduling.origin_rotation(a1))

    # 將所有路徑轉換成字串格式以方便檢查
    path_strs = set(" → ".join(node.short() for node in path) for path in paths)

    # 除錯用的輸出
    if len(path_strs) > 0:
        print("\n找到的路徑：")
        for path in path_strs:
            print(path)    # 驗證：確保不存在經過 a1 -> b2 的路徑（因為 A2 非空堂阻擋）
    a1_b2_pattern = "<1-1(x1) busy T[A] C[101]> → <1-2(x1) busy T[B] C[101]>"
    for path in path_strs:
        assert a1_b2_pattern not in path, f"發現了不應該存在的路徑模式 '{a1_b2_pattern}' 在路徑 '{path}' 中"

    # === 第三階段：其他重要驗證 ===
    # 確保每條路徑都合法
    for path in paths:
        # 檢查每一步移動是否合法
        for i in range(len(path)-1):
            curr, next_node = path[i], path[i+1]
            hop_1 = get_1_hop(curr, next_node, type="bwd")
            assert is_free(hop_1), f"路徑中存在不合法的移動：{curr.short()} -> {next_node.short()}"


def test_basic_cycle():
    """測試基本環路的所有可能組合
    
    情境：
    - 建立四位老師 A、B、C、D
    - 每位老師都有 4 節課，除了輪調課程外都是空堂
    - 環路課程安排：
      - A1：在 101 班，要輪調
      - B2：在 101 班，要和 A1 交換
      - C3：在 101 班，要和 B2 交換
      - D4：在 101 班，要和 C3 交換
    - 其他老師的課大多都在不同班級
    """
    # === 建立老師 ===
    teacher_A = TeacherNode(teacher_name="A", courses={})
    teacher_B = TeacherNode(teacher_name="B", courses={})
    teacher_C = TeacherNode(teacher_name="C", courses={})
    teacher_D = TeacherNode(teacher_name="D", courses={})
    
    # === 建立班級 ===
    cls_101 = ClassNode(class_code="101", courses={})  # 環路課程的班級
    cls_102 = ClassNode(class_code="102", courses={})  # A老師其他課程的班級
    cls_103 = ClassNode(class_code="103", courses={})  # B老師其他課程的班級
    cls_104 = ClassNode(class_code="104", courses={})  # C老師其他課程的班級
    cls_105 = ClassNode(class_code="105", courses={})  # D老師其他課程的班級

    # A 老師的課程：輪調課在 101，其他在 102
    a1 = build_course(teacher_A, cls_101, weekday=1, period=1, streak=1, is_free=False)  # 要輪調的課程（在環路中）
    a2 = build_course(teacher_A, cls_102, weekday=1, period=2, streak=1, is_free=True)
    a3 = build_course(teacher_A, cls_102, weekday=1, period=3, streak=1, is_free=True)
    a4 = build_course(teacher_A, cls_102, weekday=1, period=4, streak=1, is_free=True)
    
    # B 老師的課程：輪調課在 101，其他在 103
    b1 = build_course(teacher_B, cls_103, weekday=1, period=1, streak=1, is_free=True)
    b2 = build_course(teacher_B, cls_101, weekday=1, period=2, streak=1, is_free=False)  # 要和 a1 交換的課程（在環路中）
    b3 = build_course(teacher_B, cls_103, weekday=1, period=3, streak=1, is_free=True)
    b4 = build_course(teacher_B, cls_103, weekday=1, period=4, streak=1, is_free=True)
    
    # C 老師的課程：輪調課在 101，其他在 104 
    c1 = build_course(teacher_C, cls_104, weekday=1, period=1, streak=1, is_free=True)
    c2 = build_course(teacher_C, cls_104, weekday=1, period=2, streak=1, is_free=True)
    c3 = build_course(teacher_C, cls_101, weekday=1, period=3, streak=1, is_free=False)  # 要和 b2 交換的課程（在環路中）
    c4 = build_course(teacher_C, cls_104, weekday=1, period=4, streak=1, is_free=True)
    
    # D 老師的課程：輪調課在 101，其他在 105
    d1 = build_course(teacher_D, cls_105, weekday=1, period=1, streak=1, is_free=True)
    d2 = build_course(teacher_D, cls_105, weekday=1, period=2, streak=1, is_free=True)
    d3 = build_course(teacher_D, cls_105, weekday=1, period=3, streak=1, is_free=True)
    d4 = build_course(teacher_D, cls_101, weekday=1, period=4, streak=1, is_free=False)  # 要和 c3 交換的課程（在環路中）

    # === 執行 rotation ===
    cycles = list(scheduling.origin_rotation(a1))

    # 找到所有可能的環路組合
    sorted_cycles = sorted(cycles, key=len)
    
    print(f"\n找到 {len(cycles)} 條環路：")
    print("\n=== 依照長度排序 ===")
    current_len = 0
    for i, cycle in enumerate(sorted_cycles, 1):
        if len(cycle) != current_len:
            current_len = len(cycle)
            print(f"\n長度 {current_len}:")
        print(f"{i:2d}. {' → '.join(node.short() for node in cycle)}")

    # 將所有路徑轉換成字串形式以便比對
    path_strs = set(" → ".join(node.short() for node in cycle) for cycle in cycles)

    # 驗證基本路徑都存在
    basic_paths = {
        # 兩節課的環路 (實際長度3)
        f"{a1.short()} → {b2.short()} → {a1.short()}",
        f"{a1.short()} → {c3.short()} → {a1.short()}",
        f"{a1.short()} → {d4.short()} → {a1.short()}",

        # 三節課的環路 (實際長度4)
        f"{a1.short()} → {b2.short()} → {c3.short()} → {a1.short()}",
        f"{a1.short()} → {b2.short()} → {d4.short()} → {a1.short()}",
        f"{a1.short()} → {c3.short()} → {d4.short()} → {a1.short()}",
        f"{a1.short()} → {d4.short()} → {c3.short()} → {a1.short()}",
        f"{a1.short()} → {c3.short()} → {b2.short()} → {a1.short()}",
        f"{a1.short()} → {d4.short()} → {b2.short()} → {a1.short()}",

        # 四節課的環路 (實際長度5)
        f"{a1.short()} → {b2.short()} → {c3.short()} → {d4.short()} → {a1.short()}",
        f"{a1.short()} → {b2.short()} → {d4.short()} → {c3.short()} → {a1.short()}",
        f"{a1.short()} → {c3.short()} → {b2.short()} → {d4.short()} → {a1.short()}",
        f"{a1.short()} → {c3.short()} → {d4.short()} → {b2.short()} → {a1.short()}",
        f"{a1.short()} → {d4.short()} → {b2.short()} → {c3.short()} → {a1.short()}",
        f"{a1.short()} → {d4.short()} → {c3.short()} → {b2.short()} → {a1.short()}"
    }
    
    # 驗證找到的環路數量正確
    assert len(cycles) == len(basic_paths), f"預期找到 {len(basic_paths)} 條環路，但找到 {len(cycles)} 條"
    
    # 驗證每條基本路徑都有被找到
    for path in basic_paths:
        assert path in path_strs, f"基本路徑 {path} 未在找到的路徑中"
    
    # 驗證沒有多餘的路徑
    assert path_strs == basic_paths, "找到了預期之外的環路"

    # 驗證每條路徑都合法
    for path in cycles:
        # 確保環路首尾相連
        assert path[0] == path[-1], "環路的起點和終點必須相同"
        
        # 檢查每一步移動是否合法
        for i in range(len(path)-1):
            curr, next_node = path[i], path[i+1]
            hop_1 = get_1_hop(curr, next_node, type="bwd")
            assert is_free(hop_1), f"路徑中存在不合法的移動：{curr.short()} → {next_node.short()}"


def test_long_cycle_max_depth():
    """測試最大深度限制下的輪調環路
    
    情境：
    - 測試與 test_basic_cycle 相同的環路配置
    - 但將最大深度設為3，所以：
      1. 實際長度 = 深度 + 1（因為起點節點會重複計算在結尾）
      2. 所以深度3最多形成長度4的路徑

    可能的路徑：
    深度2路徑 (實際長度3): a1 -> b2 -> a1
    深度2路徑 (實際長度3): a1 -> c3 -> a1
    深度2路徑 (實際長度3): a1 -> d4 -> a1
    深度3路徑 (實際長度4): a1 -> b2 -> c3 -> a1
    深度3路徑 (實際長度4): a1 -> b2 -> d4 -> a1
    深度3路徑 (實際長度4): a1 -> c3 -> d4 -> a1
    等其他組合...

    不應該出現的路徑：
    深度4路徑 (實際長度5): a1 -> b2 -> c3 -> d4 -> a1
    """
    # === 建立老師 ===
    teacher_A = TeacherNode(teacher_name="A", courses={})
    teacher_B = TeacherNode(teacher_name="B", courses={})
    teacher_C = TeacherNode(teacher_name="C", courses={})
    teacher_D = TeacherNode(teacher_name="D", courses={})
    
    # === 建立班級 ===
    cls_101 = ClassNode(class_code="101", courses={})  # 環路課程的班級
    cls_102 = ClassNode(class_code="102", courses={})  # A老師其他課程的班級
    cls_103 = ClassNode(class_code="103", courses={})  # B老師其他課程的班級
    cls_104 = ClassNode(class_code="104", courses={})  # C老師其他課程的班級
    cls_105 = ClassNode(class_code="105", courses={})  # D老師其他課程的班級

    # A 老師的課程：輪調課在 101，其他在 102
    a1 = build_course(teacher_A, cls_101, weekday=1, period=1, streak=1, is_free=False)  # 要輪調的課程（在環路中）
    a2 = build_course(teacher_A, cls_102, weekday=1, period=2, streak=1, is_free=True)
    a3 = build_course(teacher_A, cls_102, weekday=1, period=3, streak=1, is_free=True)
    a4 = build_course(teacher_A, cls_102, weekday=1, period=4, streak=1, is_free=True)
    
    # B 老師的課程：輪調課在 101，其他在 103
    b1 = build_course(teacher_B, cls_103, weekday=1, period=1, streak=1, is_free=True)
    b2 = build_course(teacher_B, cls_101, weekday=1, period=2, streak=1, is_free=False)  # 要和 a1 交換的課程（在環路中）
    b3 = build_course(teacher_B, cls_103, weekday=1, period=3, streak=1, is_free=True)
    b4 = build_course(teacher_B, cls_103, weekday=1, period=4, streak=1, is_free=True)
    
    # C 老師的課程：輪調課在 101，其他在 104 
    c1 = build_course(teacher_C, cls_104, weekday=1, period=1, streak=1, is_free=True)
    c2 = build_course(teacher_C, cls_104, weekday=1, period=2, streak=1, is_free=True)
    c3 = build_course(teacher_C, cls_101, weekday=1, period=3, streak=1, is_free=False)  # 要和 b2 交換的課程（在環路中）
    c4 = build_course(teacher_C, cls_104, weekday=1, period=4, streak=1, is_free=True)
    
    # D 老師的課程：輪調課在 101，其他在 105
    d1 = build_course(teacher_D, cls_105, weekday=1, period=1, streak=1, is_free=True)
    d2 = build_course(teacher_D, cls_105, weekday=1, period=2, streak=1, is_free=True)
    d3 = build_course(teacher_D, cls_105, weekday=1, period=3, streak=1, is_free=True)
    d4 = build_course(teacher_D, cls_101, weekday=1, period=4, streak=1, is_free=False)  # 要和 c3 交換的課程（在環路中）

    # === 執行 rotation ===
    cycles = list(scheduling.origin_rotation(a1, max_depth=3))  # 設定最大深度為 3

    # 找到所有可能的環路組合
    sorted_cycles = sorted(cycles, key=len)
    
    print(f"\n找到 {len(cycles)} 條環路：")
    print("\n=== 依照長度排序 ===")
    current_len = 0
    for i, cycle in enumerate(sorted_cycles, 1):
        if len(cycle) != current_len:
            current_len = len(cycle)
            print(f"\n長度 {current_len}:")
        print(f"{i:2d}. {' → '.join(node.short() for node in cycle)}")

    # 驗證找到的環路數量正確
    expected_paths = {
        # 兩節課的環路 (實際長度3)
        f"{a1.short()} → {b2.short()} → {a1.short()}",
        f"{a1.short()} → {c3.short()} → {a1.short()}",
        f"{a1.short()} → {d4.short()} → {a1.short()}",

        # 三節課的環路 (實際長度4)
        f"{a1.short()} → {b2.short()} → {c3.short()} → {a1.short()}",
        f"{a1.short()} → {b2.short()} → {d4.short()} → {a1.short()}",
        f"{a1.short()} → {c3.short()} → {d4.short()} → {a1.short()}",
        f"{a1.short()} → {d4.short()} → {c3.short()} → {a1.short()}",
        f"{a1.short()} → {c3.short()} → {b2.short()} → {a1.short()}",
        f"{a1.short()} → {d4.short()} → {b2.short()} → {a1.short()}"
    }

    # 驗證找到的環路數量正確
    path_strs = set(" → ".join(node.short() for node in cycle) for cycle in cycles)
    assert len(cycles) == len(expected_paths), f"預期找到 {len(expected_paths)} 條環路，但找到 {len(cycles)} 條"
    
    # 驗證每條基本路徑都有被找到
    for path in expected_paths:
        assert path in path_strs, f"基本路徑 {path} 未在找到的路徑中"
    
    # 驗證沒有多餘的路徑
    assert path_strs == expected_paths, "找到了預期之外的環路"

    # 驗證每條路徑都合法
    for path in cycles:
        # 確保環路首尾相連
        assert path[0] == path[-1], "環路的起點和終點必須相同"
        
        # 檢查每一步移動是否合法
        for i in range(len(path)-1):
            curr, next_node = path[i], path[i+1]
            hop_1 = get_1_hop(curr, next_node, type="bwd")
            assert is_free(hop_1), f"路徑中存在不合法的移動：{curr.short()} → {next_node.short()}"

        # 驗證路徑長度不超過最大深度限制
        assert len(path) <= 4, "路徑長度超過最大深度限制"  # max_depth=3 時，最長路徑為 4（包含重複的起點）


def test_isolated_course():
    """測試孤立課程的情況
    
    情境：
    - 建立一個孤立的課程節點（沒有任何連接）
    - 建立一個班級和一位老師
    - 所有課程都在同一個班級中
    
    檢查項目：
    1. 確認孤立的課程節點無法形成環路
    2. rotation 函數應該返回空列表
    """
    # === 建立老師與班級 ===
    teacher_A = TeacherNode(teacher_name="A", courses={})
    cls_101 = ClassNode(class_code="101", courses={})    # === 建立班級 ===
    cls_102 = ClassNode(class_code="102", courses={})  # 使用另一個班級，確保課程真的是孤立的

    # === 建立課程節點 ===
    a1 = build_course(teacher_A, cls_101, weekday=1, period=1, streak=1, is_free=False)  
    a2 = build_course(teacher_A, cls_102, weekday=1, period=2, streak=1, is_free=True)   

    # === 執行 rotation ===
    cycles = list(scheduling.origin_rotation(a1))
    
    # === 驗證：不應該找到任何環路 ===
    assert len(cycles) == 0, "孤立的課程節點不應該能找到任何輪調環路"

    # === 額外驗證：確保 a1 確實是孤立的 ===
    neighbors = list(cls_101.courses.values())
    assert len(neighbors) >= 1, "班級應該至少有一節課程"
    assert a1 in neighbors, "孤立的課程節點應該在班級的課程列表中"

@pytest.mark.asyncio
async def test_yan_young_jing_3_2():
    """測試顏永進老師的 3-2 課程配置
    """
    result = await scheduling.rotation("顏永進", weekday=3, period=3, max_depth=5)
    print(result)