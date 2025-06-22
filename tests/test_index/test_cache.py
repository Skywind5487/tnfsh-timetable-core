import pytest
import os
import json
from pathlib import Path
from datetime import datetime
from tnfsh_timetable_core.index.cache import IndexCache
from tnfsh_timetable_core.index.models import CachedFullIndex, CacheMetadata, FullIndexResult, DetailedIndex, NewGroupIndex, NewCategoryMap


@pytest.fixture
def cache(tmp_path):
    """建立測試用的快取實例，使用臨時目錄避免污染"""
    cache_file = tmp_path / "test_index_cache.json"
    return IndexCache(file_path=str(cache_file))


@pytest.mark.asyncio
async def test_memory_and_file_cache(cache: IndexCache, tmp_path):
    """測試記憶體與檔案快取的優先順序與一致性"""
    # 第一次強制從網路取得並寫入檔案與記憶體
    result1 = await cache.fetch(refresh=True)
    assert isinstance(result1, CachedFullIndex)
    # 檔案應已寫入
    assert cache._cache_file.exists()
    # 第二次應從記憶體快取取得
    result2 = await cache.fetch(refresh=False)
    assert result2 is not None
    assert result1.model_dump() == result2.model_dump()
    # 清除記憶體快取，強制從檔案取得
    from tnfsh_timetable_core.index.cache import _memory_cache

    _memory_cache = None
    result3 = await cache.fetch(refresh=False)
    assert result3 is not None
    assert result1.model_dump() == result3.model_dump()


@pytest.mark.asyncio
async def test_reverse_index_consistency(cache: IndexCache):
    """測試反向索引與正向索引資料一致性"""
    result: CachedFullIndex = await cache.fetch(refresh=True)
    # 取一個教師與班級
    teacher_data = next(iter(result.data.index.teacher.data.values()))
    class_data = next(iter(result.data.index.class_.data.values()))
    teacher_name = next(iter(teacher_data.keys()))
    class_code = next(iter(class_data.keys()))
    # 反向索引必須包含這些 key
    assert teacher_name in result.data.reverse_index
    assert class_code in result.data.reverse_index
    # URL 必須一致
    assert result.data.reverse_index[teacher_name]["url"] == teacher_data[teacher_name]
    assert result.data.reverse_index[class_code]["url"] == class_data[class_code]


@pytest.mark.asyncio
async def test_cache_file_corruption(cache: IndexCache):
    """測試快取檔案損壞時能自動 fallback 到網路"""
    # 先寫入損壞檔案
    with open(cache._cache_file, "w", encoding="utf-8") as f:
        f.write("not a valid json")
    # 取得時應自動 fallback 並修正
    result = await cache.fetch(refresh=False)
    assert isinstance(result, CachedFullIndex)
    # 檔案應已被正確覆蓋
    with open(cache._cache_file, encoding="utf-8") as f:
        data = json.load(f)
    assert "index" in data or "data" in data


@pytest.mark.asyncio
async def test_cache_file_permission_error(tmp_path):
    """測試快取檔案無法寫入時會拋出例外"""
    cache_file = tmp_path / "readonly_cache.json"
    cache_file.write_text("{}", encoding="utf-8")
    os.chmod(cache_file, 0o444)  # 設為唯讀
    cache = IndexCache(file_path=str(cache_file))
    # 建立最小合法的 CachedFullIndex
    empty_group = NewGroupIndex(url="", last_update="2020/01/01 00:00:00", data=NewCategoryMap({}))
    dummy = CachedFullIndex(
        metadata=CacheMetadata(cache_fetch_at=datetime.now()),
        data=FullIndexResult(
            detailed_index=DetailedIndex(
                base_url="", root="", last_update="2020/01/01 00:00:00",
                class_=empty_group, teacher=empty_group
            ),
            id_to_info={},
            target_to_unique_info={},
            target_to_conflicting_ids={}
        )
    )
    try:
        with pytest.raises(Exception):
            await cache.save_to_file(dummy)
    finally:
        os.chmod(cache_file, 0o666)  # 恢復權限


@pytest.mark.asyncio
async def test_cache_fields_consistency(cache: IndexCache):
    """測試 CachedFullIndex 其他欄位的結構與資料一致性"""
    result: CachedFullIndex = await cache.fetch(refresh=True)
    data = result.data
    # detailed_index 結構
    assert hasattr(data, "detailed_index")
    assert hasattr(data.detailed_index, "class_")
    assert hasattr(data.detailed_index, "teacher")
    assert isinstance(data.detailed_index.class_, NewGroupIndex)
    assert isinstance(data.detailed_index.teacher, NewGroupIndex)
    # id_to_info/target_to_unique_info/target_to_conflicting_ids 型別
    assert isinstance(data.id_to_info, dict)
    assert isinstance(data.target_to_unique_info, dict)
    assert isinstance(data.target_to_conflicting_ids, dict)
    # id_to_info 內容驗證
    if data.id_to_info:
        any_id, any_info = next(iter(data.id_to_info.items()))
        assert isinstance(any_id, str)
        assert hasattr(any_info, "target")
        # target_to_unique_info 也能查到 target
        if any_info.target in data.target_to_unique_info:
            assert data.target_to_unique_info[any_info.target].target == any_info.target
    # target_to_conflicting_ids 驗證
    for target, id_list in data.target_to_conflicting_ids.items():
        assert isinstance(id_list, list)
        assert len(id_list) > 1 or target not in data.target_to_unique_info
    # 驗證 target -> id 的唯一性與衝突情境
    for target in set(list(data.target_to_unique_info.keys()) + list(data.target_to_conflicting_ids.keys())):
        if target in data.target_to_unique_info:
            # 唯一 target，不能在 conflicting_ids
            assert target not in data.target_to_conflicting_ids
            info = data.target_to_unique_info[target]
            # id_to_info 必有此 id
            assert info.id in data.id_to_info
            assert data.id_to_info[info.id].target == target
        else:
            # 有衝突的 target，必在 conflicting_ids 且 id list > 1
            assert target in data.target_to_conflicting_ids
            id_list = data.target_to_conflicting_ids[target]
            assert isinstance(id_list, list)
            assert len(id_list) > 1
            # 每個 id 都能在 id_to_info 查到，且 target 一致
            for _id in id_list:
                assert _id in data.id_to_info
                assert data.id_to_info[_id].target == target
