from tkinter import PIESLICE


async def get_course_info(
    target: str = "307",
    weekday: int = 1,
    period: int = 1
):
    """獲取指定班級或老師的課程資訊

    Args:
        target: 班級代碼或老師名稱（如: "307" 或 "顏永進"），預設為"307"
        weekday: 星期幾（1-7，預設為1，即星期一）
        period: 節次（1-8，預設為1，即第一節）
    """
    
    # 初始化 core
    from tnfsh_timetable_core import TNFSHTimetableCore
    core = TNFSHTimetableCore()
    
    # 獲取課程資訊
    timetable = await core.fetch_timetable(target)
    table = timetable.table
    course_info = table[weekday-1][period-1]
    print(f"🎓 課程資訊: {target}星期{weekday}第{period}節")
    print(course_info.model_dump_json(indent=4))

if __name__ == "__main__":
    import asyncio
    import time
    start_time = time.time()
    asyncio.run(get_course_info("307", 4, 5))  # 可以替換成其他班級代碼或老師名稱
    end_time = time.time()
    print(f"執行時間: {end_time - start_time:.2f} 秒")