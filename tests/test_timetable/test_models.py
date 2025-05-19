import pytest
import asyncio
from tnfsh_timetable_core.timetable.models import TimeTable
from tnfsh_timetable_core.utils.logger import get_logger

logger = get_logger(logger_level="INFO")
print("fetch_cached =", TimeTable.fetch_cached)
print("is method =", isinstance(TimeTable.fetch_cached, classmethod))

@pytest.mark.asyncio
async def test_class_table_fetch():
    """測試課表載入功能"""
    logger.info("🚀 開始測試課表載入")
    table = await TimeTable.fetch_cached(target="317", refresh=True)
    logger.info("✨ 測試完成，輸出課表資料")
    
    # 驗證結果
    assert table is not None
    assert table.type == "class"
    assert table.target == "317"
    assert len(table.table) > 0
    
    # 檢查課表結構
    assert len(table.table) == 5  # 週一到週五
    assert all(len(day) == 8 for day in table.table)  # 每天8節課

if __name__ == "__main__":
    asyncio.run(test_class_table_fetch())