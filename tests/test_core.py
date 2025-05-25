import tabnanny
from tnfsh_timetable_core import TNFSHTimetableCore
import pytest
import asyncio

@pytest.mark.asyncio
async def test_timetable_core():
    core: TNFSHTimetableCore = TNFSHTimetableCore()
    index = core.fetch_index()
    timetable = await core.fetch_timetable(target="307")
    assert True

async def get_timetable():
    core = TNFSHTimetableCore()
    from tnfsh_timetable_core.timetable.models import TimeTable
    timetable:TimeTable = await core.fetch_timetable(target="311")
    table = timetable.table
    teacher_name = set()
    for day in table:
        for period in day:
            if period is None:
                continue
            for counterpart in period.counterpart:
                print(counterpart.participant)
                teacher_name.add(counterpart.participant)
    print(teacher_name)
    return teacher_name

async def get_specific_course():
    core = TNFSHTimetableCore()
    table = await core.fetch_timetable("陳暐捷")
    table = table.table
    for day_index, day in enumerate(table):
        print(f"Day: {day_index}")
        for period_index, period in enumerate(day):
            print(f"  Period {period_index}: {period}")
    return table

if __name__ == "__main__":
    #asyncio.run(test_timetable_core())

    #time_table = TNFSHTimetableCore().get_timetable(target="307")
    asyncio.run(get_specific_course())    