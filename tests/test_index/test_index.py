import asyncio
import json
from pathlib import Path
import pytest
from datetime import datetime
from tnfsh_timetable_core.index.index import Index

@pytest.mark.asyncio
async def test_init():
    """測試基本初始化"""
    index = Index()
    assert index.base_url == "http://w3.tnfsh.tn.edu.tw/deanofstudies/course/"
    assert index.index is None
    assert index.reverse_index is None

@pytest.mark.asyncio
async def test_fetch_basic():
    """測試基本的索引獲取功能"""
    index = await Index.fetch()
    assert index.index is not None
    assert index.reverse_index is not None
    assert len(index.index.teacher.data) > 0
    assert len(index.index.class_.data) > 0

@pytest.mark.asyncio
async def test_fetch_with_refresh():
    """測試強制更新功能"""
    # 先獲取一次資料
    index1 = await Index.fetch()
    first_data = index1.index.model_dump_json()
    
    # 強制更新再獲取一次
    index2 = await Index.fetch(refresh=True)
    second_data = index2.index.model_dump_json()
    
    # 資料應該要相同（假設在測試期間資料沒有更新）
    assert first_data == second_data

@pytest.mark.asyncio
async def test_custom_base_url():
    """測試自訂 base_url"""
    custom_url = "https://example.com/course/"
    index = Index(base_url=custom_url)
    assert index.base_url == custom_url

@pytest.mark.asyncio
async def test_export_json_all(tmp_path: Path):
    """測試匯出所有資料為 JSON"""
    index = await Index.fetch()
    json_path = tmp_path / "test_index.json"
    filepath = index.export_json(export_type="all", filepath=str(json_path))
    assert json_path.exists()
    # 驗證匯出的 JSON 內容
    data = json.loads(json_path.read_text(encoding='utf-8'))
    # 頂層欄位
    assert "metadata" in data
    assert "data" in data
    # metadata 欄位
    assert "cache_fetch_at" in data["metadata"]
    # data 欄位
    for key in [
        "index", "reverse_index", "detailed_index",
        "id_to_info", "target_to_unique_info", "target_to_conflicting_ids"
    ]:
        assert key in data["data"]

@pytest.mark.asyncio
async def test_export_json_index_only(tmp_path: Path):
    """測試只匯出正向索引"""
    index = await Index.fetch()
    json_path = tmp_path / "test_index.json"
    filepath = index.export_json(export_type="index", filepath=str(json_path))
    
    data = json.loads(json_path.read_text(encoding='utf-8'))
    
    # IndexResult 應有的欄位
    for key in ["base_url", "root", "class_", "teacher"]:
        assert key in data["data"]
    assert "reverse_index" not in data["data"]

@pytest.mark.asyncio
async def test_export_json_reverse_only(tmp_path: Path):
    """測試只匯出反向索引"""
    index = await Index.fetch()
    json_path = tmp_path / "test_index.json"
    filepath = index.export_json(export_type="reverse_index", filepath=str(json_path))
    data = json.loads(json_path.read_text(encoding='utf-8'))
    # ReverseIndexResult 是 dict，key 應該是 target name
    assert isinstance(data["data"], dict)
    # 應該有一些 key（target name），且沒有 "index"、"base_url" 等
    assert len(data["data"]) > 0
    assert "index" not in data["data"]
    assert "base_url" not in data["data"]

@pytest.mark.asyncio
async def test_getitem_success():
    """測試成功獲取課表 URL"""
    index = await Index.fetch()
    
    # 取得第一個教師和班級進行測試
    teacher = index.get_all_teachers()[0]
    class_ = index.get_all_classes()[0]
    
    # 測試教師和班級的 URL 獲取
    assert index[teacher].url.endswith("html") or index[teacher].url.endswith("HTML")
    assert index[class_].url.endswith("html") or index[class_].url.endswith("HTML")

@pytest.mark.asyncio
async def test_getitem_not_found():
    """測試找不到課表時的錯誤處理"""
    index = await Index.fetch()
    
    with pytest.raises(KeyError):
        _ = index["不存在的課表"]

@pytest.mark.asyncio
async def test_export_json_invalid_type():
    """測試無效的匯出類型"""
    index = await Index.fetch()
    
    with pytest.raises(ValueError):
        index.export_json(export_type="invalid_type")

@pytest.mark.asyncio
async def test_uninitialized_operations():
    """測試未初始化時的操作"""
    index = Index()
    
    # 測試未初始化時的 export_json
    with pytest.raises(RuntimeError):
        index.export_json()
    
    # 測試未初始化時的 __getitem__
    with pytest.raises(RuntimeError):
        _ = index["某班級"]

if __name__ == "__main__":
    asyncio.run(test_fetch_basic())
