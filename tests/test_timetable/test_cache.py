import pytest
import asyncio
from tnfsh_timetable_core.timetable.cache import preload_all
from tnfsh_timetable_core.utils.logger import get_logger

logger = get_logger(logger_level="INFO")

@pytest.mark.asyncio
async def test_preload_all():
    """測試預載入所有課表"""
    await preload_all(only_missing=True, max_concurrent=5)


if __name__ == "__main__":
    asyncio.run(test_preload_all())