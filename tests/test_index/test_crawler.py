import asyncio
import pytest
from tnfsh_timetable_core.index.crawler import IndexCrawler

@pytest.mark.asyncio
async def test_index():
    """測試獲取所有索引"""
    base_url = "http://w3.tnfsh.tn.edu.tw/deanofstudies/course/"
    crawler = IndexCrawler(base_url=base_url)

    
    from tnfsh_timetable_core.index.models import IndexResult
    result: IndexResult = await crawler.fetch()

    temp_path = "tests/assets/index/crawler/index_result.json"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(indent=4))
    
    assert result is not None



if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_index())
