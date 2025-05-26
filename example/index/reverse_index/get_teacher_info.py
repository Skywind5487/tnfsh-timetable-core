async def get_teacher_info(teacher_name: str=None):
    """獲取指定老師的課程資訊"""
    if not teacher_name:
        teacher_name =  "顏永進"  # 預設老師名稱，若未提供則使用此值
    # 初始化 core
    
    from tnfsh_timetable_core import TNFSHTimetableCore
    core = TNFSHTimetableCore()
    index = await core.fetch_index()
    
    # 獲取老師的課程資訊
    teacher_info = index.reverse_index.root[teacher_name]
    print(f"🎓 老師名稱: {teacher_name}")
    print(teacher_info.model_dump_json(indent=4))


if __name__ == "__main__":
    import asyncio
    asyncio.run(get_teacher_info("顏永進"))  # 可以替換成其他老師名稱
