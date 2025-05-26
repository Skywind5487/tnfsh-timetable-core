async def yan_young_jing_3_2():
    """測試顏永進老師的 3-2 課程 一節的配置
    """    
    # 初始化 core
    from tnfsh_timetable_core import TNFSHTimetableCore
    core = TNFSHTimetableCore()
    # 調用 scheduling
    scheduling = core.fetch_scheduling()
    # 搜尋顏永進老師週三第2節的交換路徑
    cycles = await scheduling.swap("顏永進", weekday=3, period=2, max_depth=1, refresh=False)
    # max_depth: 在交換中，max_depth代表一組(兩人)老師的課要「交換」幾次
    cycles_list = list(cycles)

    # 列印找到的互換路徑
    print(f"\n找到 {len(cycles_list)} 條路：")
    if cycles_list:
        print("\n=== 互換路徑 ===")
        for i, cycle in enumerate(cycles_list, 1):
            print(f"\n路徑 {i}:")
            # 跳過第一個和最後一個節點
            path = cycle[1:-1]
            
            # 每兩個節點一組進行輸出
            for j in range(0, len(path), 2):
                if j + 1 < len(path):  # 確保有下一個節點
                    node1, node2 = path[j], path[j+1]
                    
                    # 取得節點1的資訊
                    teacher1 = ','.join(t.teacher_name for t in node1.teachers.values())
                    class1 = ','.join(c.class_code for c in node1.classes.values())
                    
                    # 取得節點2的資訊
                    teacher2 = ','.join(t.teacher_name for t in node2.teachers.values())
                    class2 = ','.join(c.class_code for c in node2.classes.values())

                    print(f"將 {teacher1} 老師週{node1.time.weekday}第{node1.time.period}節{str(node1.time.streak)+"連堂" if node1.time.streak and node1.time.streak != 1 else ''} ({class1}) "
                          f"與 {teacher2} 老師週{node2.time.weekday}第{node2.time.period}節{str(node2.time.streak)+"連堂" if node2.time.streak and node2.time.streak != 1 else ''} ({class2}) 互換")
    else:
        print("沒有找到任何互換路徑")

if __name__ == "__main__":
    import asyncio
    asyncio.run(yan_young_jing_3_2())
