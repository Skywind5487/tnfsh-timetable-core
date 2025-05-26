async def get_grade_info(grade: str=None):
    """獲取指定年級的課程資訊
    
    Args:
        grade: 年級（高一、高二、高三），若未提供則預設為高一
    """
    if not grade:
        grade = "高一"  # 預設年級
    grade_name = grade
    
    # 初始化 core
    from tnfsh_timetable_core import TNFSHTimetableCore
    core = TNFSHTimetableCore()
    index = await core.fetch_index()
    
    # 獲取年級的課程資訊
    grade_info = index.index.class_.data[grade_name]
    print(f"年級: {grade}")
    import json
    print(json.dumps(grade_info, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    import asyncio
    asyncio.run(get_grade_info("高一"))  # 可以替換成其他年級（高一、高二、高三）
