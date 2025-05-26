import time


async def get_class_or_teacher_timetable(
    target: str = None,
):
    """獲取指定班級或老師的課程資訊

    Args:
        class_code: 班級代碼（如: "307"），若未提供則預設為"307"
        teacher_name: 老師名稱（如: "顏永進"），若未提供則預設為"顏永進"
    """

    # 初始化 core
    from tnfsh_timetable_core import TNFSHTimetableCore
    core = TNFSHTimetableCore()
    
    if not target:
        target = "307"
    
    # 獲取課程資訊
    timetable = await core.fetch_timetable(target)
    print(f"🎓 課程資訊: {target}")
    print(timetable.model_dump_json(indent=4))

if __name__ == "__main__":  
    import asyncio
    start_time = time.time()
    asyncio.run(get_class_or_teacher_timetable("307"))  # 可以替換成其他班級代碼或老師名稱
    end_time = time.time()
    print(f"執行時間: {end_time - start_time:.2f} 秒")