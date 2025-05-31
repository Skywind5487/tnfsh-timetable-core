"""基本輪調範例：展示如何使用 rotation 功能

這個範例展示：
1. 如何初始化 TNFSHTimetableCore
2. 如何使用 rotation 函數搜尋輪調路徑
3. 如何格式化輸出輪調結果
"""
import asyncio
from tnfsh_timetable_core import TNFSHTimetableCore

async def yan_young_jing_2_4():
    """測試顏永進老師的 2-4兩節的 課程配置
    """    
    
    # 初始化 core
    core = TNFSHTimetableCore()
    # 調用 scheduling
    scheduling = await core.fetch_scheduling()
    # 搜尋顏永進老師週二第4節的輪調路徑
    cycles = await scheduling.rotation("顏永進", weekday=3, period=2, max_depth=2, refresh=False)
    # max_depth: 在輪換中，max_depth代表老師的課要「移動」幾次
    cycles_list = list(cycles)
    
    
    # 列印找到的環路
    print(f"\n找到 {len(cycles_list)} 條環路：")
    if cycles_list:
        print("\n=== 輪調路徑 ===")
        for i, cycle in enumerate(cycles_list, 1):
            print(f"\n路徑 {i}:")
            # 依序處理每一步移動
            for j in range(len(cycle)-1):
                node1, node2 = cycle[j], cycle[j+1]
                
                # 取得節點資訊
                teacher1 = ','.join(t.teacher_name for t in node1.teachers.values())
                class1 = ','.join(c.class_code for c in node1.classes.values())
                teacher2 = ','.join(t.teacher_name for t in node2.teachers.values())
                class2 = ','.join(c.class_code for c in node2.classes.values())

                print(f"將 {teacher1} 老師週{node1.time.weekday}第{node1.time.period}節的課{str(node1.time.streak)+"連堂" if node1.time.streak and node1.time.streak != 1 else ''} ({class1}) "
                      f"搬到 週{node2.time.weekday}第{node2.time.period}節{str(node2.time.streak)+"連堂" if node2.time.streak and node2.time.streak != 1 else ''} ({class2})")
    else:
        print("沒有找到任何輪調路徑")


if __name__ == "__main__":
    asyncio.run(yan_young_jing_2_4())
