import asyncio
import pytest
from tnfsh_timetable_core.index.models import IndexResult, GroupIndex, ReverseMap, AllTypeIndexResult
from tnfsh_timetable_core.index.crawler import reverse_index, fetch_all_index

@pytest.mark.asyncio
async def test_all_index():
    """測試獲取所有索引"""
    
    base_url = "http://w3.tnfsh.tn.edu.tw/deanofstudies/course/"
    result: AllTypeIndexResult = await fetch_all_index(base_url)
    
    assert result is not None
    print(result.model_dump_json(indent=4))

@pytest.mark.asyncio
async def test_reverse_index():
    """測試 reverse_index 函數的轉換功能"""
    
    # 建立測試資料
    index = IndexResult(
        base_url="http://example.com/",
        root="index.html",
        class_=GroupIndex(
            url="_ClassIndex.html",
            data={
                "高一": {
                    "101": "C101101.html",
                    "102": "C101102.html"
                },
                "高二": {
                    "201": "C102201.html"
                }
            }
        ),
        teacher=GroupIndex(
            url="_TeachIndex.html",
            data={
                "國文科": {
                    "王大明": "TA01.html",
                    "李小華": "TA02.html"
                },
                "數學科": {
                    "張三": "TB01.html"
                }
            }
        )
    )
    
    # 執行轉換
    result = reverse_index(index)
    
    # 驗證結果
    # 測試班級資料
    assert result["101"].url == "C101101.html"
    assert result["101"].category == "高一"
    assert result["102"].url == "C101102.html"
    assert result["102"].category == "高一"
    assert result["201"].url == "C102201.html"
    assert result["201"].category == "高二"
    
    # 測試教師資料
    assert result["王大明"].url == "TA01.html"
    assert result["王大明"].category == "國文科"
    assert result["李小華"].url == "TA02.html"
    assert result["李小華"].category == "國文科"
    assert result["張三"].url == "TB01.html"
    assert result["張三"].category == "數學科"

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_all_index())
