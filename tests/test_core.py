from tnfsh_timetable_core import TNFSHTimetableCore
async def test_timetable_core():
    core = TNFSHTimetableCore()
    index = core.index()
    timetable = core.timetable()
