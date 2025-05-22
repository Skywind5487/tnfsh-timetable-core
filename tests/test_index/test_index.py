import asyncio
import pytest
from tnfsh_timetable_core.index.index import Index

@pytest.mark.asyncio
async def test_fetch_index():
    """測試獲取完整的課表索引"""

    index = Index()
    await index.fetch(refresh=True)  # 使用正確的方法名稱
    
    assert index.index is not None
    assert index.reverse_index is not None
    
    index_2 = Index()
    await index_2.fetch(refresh=True)
    
    assert index_2.index == index.index    
    #print(index.index.model_dump_json(indent=4))

if __name__ == "__main__":
    asyncio.run(test_fetch_index())
