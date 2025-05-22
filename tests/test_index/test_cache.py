import asyncio
import pytest
from datetime import datetime
from tnfsh_timetable_core.index.cache import fetch_with_cache

@pytest.mark.asyncio
async def test_fetch_with_cache():
    """測試快取機制"""
    base_url = "http://w3.tnfsh.tn.edu.tw/deanofstudies/course/"
    result = await fetch_with_cache(base_url, refresh=True)
    assert result is not None
    # print(result.model_dump_json(indent=4))



if __name__ == "__main__":
    asyncio.run(test_fetch_with_cache())
