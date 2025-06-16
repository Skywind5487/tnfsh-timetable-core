import asyncio
import pytest
from pathlib import Path
from tnfsh_timetable_core.index.cache import IndexCache
from tnfsh_timetable_core.index.models import IndexResult, AllTypeIndexResult, ReverseIndexResult

@pytest.fixture
def cache():
    """建立測試用的快取實例"""
    return IndexCache()


@pytest.mark.asyncio
async def test_memory_cache(cache: IndexCache):
    """測試記憶體快取機制"""
    # 第一次從源頭取得
    result1 = await cache.fetch(refresh=True)
    assert result1 is not None
    
    # 第二次應該從記憶體快取取得
    result2 = await cache.fetch(refresh=False)
    assert result2 is not None
    assert result1.model_dump() == result2.model_dump()  # 應該是相同的資料



@pytest.mark.asyncio
async def test_reverse_index_creation(cache: IndexCache):
    """測試反向索引的建立"""
    result = await cache.fetch(refresh=True)
    
    # 選擇一個教師和班級來測試
    teacher_data = next(iter(result.index.teacher.data.values()))
    class_data = next(iter(result.index.class_.data.values()))
    
    teacher_name = next(iter(teacher_data.keys()))
    class_code = next(iter(class_data.keys()))
    
    # 檢查反向索引是否包含這些項目
    assert teacher_name in result.reverse_index
    assert class_code in result.reverse_index
    
    # 檢查 URL 是否一致
    assert result.reverse_index[teacher_name]["url"] == teacher_data[teacher_name]
    assert result.reverse_index[class_code]["url"] == class_data[class_code]
