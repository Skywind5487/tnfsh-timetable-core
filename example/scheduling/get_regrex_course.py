async def get_streak_start_node():
    # core
    from tnfsh_timetable_core import TNFSHTimetableCore
    core = TNFSHTimetableCore()
    scheduling = await core.fetch_scheduling()
    # 獲取連續課程的起始節次
    from tnfsh_timetable_core.scheduling.models import CourseNode
    course_node: CourseNode = await scheduling.fetch_course_node(
        "顏永進", 
        weekday=3, 
        period=2)
    print(f"連續課程起始節:")
    print(course_node.short())

if __name__ == "__main__":
    import asyncio
    asyncio.run(get_streak_start_node())