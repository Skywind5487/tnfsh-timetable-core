import pytest
import asyncio
import json
from bs4 import BeautifulSoup
from tnfsh_timetable_core.timetable.crawler import fetch_raw_html, parse_html
from tnfsh_timetable_core.utils.logger import get_logger

# 設定日誌
logger = get_logger(logger_level="INFO")


@pytest.mark.asyncio
async def test_fetch_and_parse_timetable(tmp_path):
    """測試抓取和解析課表並寫入 temp 資料夾"""
    target = "307"
    logger.info(f"🚀 開始抓取課表：{target}")
    
    html_content = await fetch_raw_html(target)
    parsed_result = parse_html(html_content)
    logger.info(f"✨ 課表抓取完成：{target}")

    # 在 tmp_path 中建立臨時 HTML 檔案
    save_path = tmp_path / "class_307.html"
    save_path.write_text(html_content.prettify(), encoding="utf-8")
    logger.info(f"💾 已儲存 HTML 至：{save_path}")

    # 顯示解析結果
    logger.debug("📝 輸出解析結果")
    print(json.dumps(parsed_result, ensure_ascii=False, indent=4))

    # 驗證結果
    assert parsed_result is not None
    assert "last_update" in parsed_result
    assert "periods" in parsed_result
    assert "table" in parsed_result
    assert len(parsed_result["table"]) > 0



if __name__ == "__main__":
    asyncio.run(test_fetch_and_parse_timetable())