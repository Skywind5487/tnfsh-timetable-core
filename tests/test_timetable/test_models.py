import pytest
import asyncio
from tnfsh_timetable_core.timetable.models import TimeTable
from tnfsh_timetable_core.utils.logger import get_logger

logger = get_logger(logger_level="INFO")

@pytest.mark.asyncio
async def test_class_table_fetch():
    """測試課表載入功能"""
    logger.info("🚀 開始測試課表載入")
    table = await TimeTable.fetch_cached("317", refresh=True)
    logger.info("✨ 測試完成，輸出課表資料")
    
    # 驗證結果
    assert table is not None
    assert table.type == "class"
    assert table.target == "317"
    assert len(table.table) > 0
