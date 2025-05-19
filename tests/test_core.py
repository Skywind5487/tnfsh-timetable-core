from tnfsh_timetable_core import TNFSHTimetableCore
import pytest

@pytest.mark.asyncio
async def test_timetable_core():
    core: TNFSHTimetableCore = TNFSHTimetableCore()
    index = core.fetch_index()
    timetable = await core.fetch_timetable(target="307")
    assert True

if __name__ == "__main__":
    test_timetable_core()