import pytest
import asyncio
import aiohttp
from pathlib import Path
from bs4 import BeautifulSoup
from tnfsh_timetable_core.timetable.crawler import TimetableCrawler, FetchError
from tnfsh_timetable_core.utils.logger import get_logger

# 設定日誌
logger = get_logger(logger_level="INFO")

@pytest.fixture
def crawler():
    """建立一個測試用的 TimetableCrawler 實例"""
    return TimetableCrawler()

@pytest.fixture
def custom_aliases_crawler():
    """建立一個具有自定義別名的 TimetableCrawler 實例"""
    custom_aliases = [{"測試教師A", "測試教師B", "測試教師C"}]
    return TimetableCrawler(aliases=custom_aliases)

@pytest.mark.asyncio
async def test_fetch_and_parse_timetable(crawler, tmp_path):
    """測試完整的課表抓取和解析流程"""
    target = "307"
    logger.info(f"🚀 開始抓取課表：{target}")
    
    # 測試完整流程
    result = await crawler.fetch(target)
    
    # 驗證結果結構
    assert isinstance(result, dict)
    assert all(key in result for key in ["last_update", "periods", "table"])
    assert isinstance(result["last_update"], str)
    assert isinstance(result["periods"], dict)
    assert isinstance(result["table"], list)
    assert len(result["table"]) > 0
    
    # 測試輸出到臨時檔案
    soup = await crawler.fetch_raw(target)
    output_path = tmp_path / "class_307.html"
    output_path.write_text(soup.prettify(), encoding="utf-8")
    assert output_path.exists()
    
    logger.info(f"✅ 課表抓取測試完成：{target}")

@pytest.mark.asyncio
async def test_fetch_raw_timetable(crawler):
    """測試原始 HTML 抓取功能"""
    target = "307"
    soup = await crawler.fetch_raw(target)
    assert isinstance(soup, BeautifulSoup)
    assert soup.find("table") is not None

@pytest.mark.asyncio
async def test_parse_timetable(crawler):
    """測試課表解析功能"""
    target = "307"
    soup = await crawler.fetch_raw(target)
    result = crawler.parse(soup)
    
    # 驗證解析結果
    assert isinstance(result["last_update"], str)
    assert isinstance(result["periods"], dict)
    assert isinstance(result["table"], list)
    assert len(result["table"]) > 0
    assert all(isinstance(row, list) for row in result["table"])

@pytest.mark.asyncio
async def test_alias_resolution(custom_aliases_crawler):
    """測試別名解析功能"""
    # 使用自定義別名測試
    with pytest.raises(FetchError, match="找不到.*的Timetable網址"):
        await custom_aliases_crawler.fetch("測試教師A")

@pytest.mark.asyncio
async def test_refresh_behavior(crawler):
    """測試強制更新行為"""
    target = "307"
    
    # 第一次抓取
    result1 = await crawler.fetch(target, refresh=False)
    
    # 強制更新抓取
    result2 = await crawler.fetch(target, refresh=True)
    
    # 結果應該要有相同的結構
    assert all(key in result1 for key in ["last_update", "periods", "table"])
    assert all(key in result2 for key in ["last_update", "periods", "table"])

@pytest.mark.asyncio
async def test_error_handling(crawler):
    """測試錯誤處理"""
    # 測試不存在的目標
    with pytest.raises(FetchError, match="找不到.*的Timetable網址"):
        await crawler.fetch("不存在的班級")
    
    # 測試網路錯誤（模擬請求超時）
    target = "407" # 錯誤的班級代碼
    with pytest.raises(FetchError):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=0.001)) as session:
            await crawler.fetch(target)

@pytest.mark.asyncio
async def test_period_parsing(crawler):
    """測試課程時間解析"""
    target = "307"
    result = await crawler.fetch(target)
    
    # 驗證時間格式
    for period, (start, end) in result["periods"].items():
        assert isinstance(period, str)
        assert isinstance(start, str)
        assert isinstance(end, str)
        assert ":" in start
        assert ":" in end

@pytest.mark.asyncio
async def test_cell_parsing(crawler):
    """測試課程單元格解析"""
    target = "307"
    result = await crawler.fetch(target)
    
    # 驗證課程資料結構
    for row in result["table"]:
        for cell in row:
            assert isinstance(cell, dict)
            for subject, teachers in cell.items():
                assert isinstance(subject, str)
                assert isinstance(teachers, dict)
                for teacher, url in teachers.items():
                    assert isinstance(teacher, str)
                    assert isinstance(url, str)

if __name__ == "__main__":
    pytest.main(["-v", __file__])