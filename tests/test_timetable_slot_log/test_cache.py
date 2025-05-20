import pytest
from pathlib import Path
import json
from tnfsh_timetable_core.timetable_slot_log.cache import TimetableSlotLogCache, _memory_cache
from tnfsh_timetable_core.timetable_slot_log.timetable_slot_log import TimetableSlotLog, TimetableSlotLogDict
from tnfsh_timetable_core.timetable_slot_log.models import StreakTime
from tnfsh_timetable_core.timetable.models import CourseInfo

@pytest.fixture
def sample_logs():
    """建立測試資料"""
    return [
        TimetableSlotLog(
            source="class_001",
            streak_time=StreakTime(weekday=1, period=1, streak=2),
            log=CourseInfo(subject="數學")
        ),
        TimetableSlotLog(
            source="class_001",
            streak_time=StreakTime(weekday=1, period=3, streak=1),
            log=None
        )
    ]

@pytest.fixture
def sample_dict(sample_logs):
    """將測試資料轉換為字典格式"""
    result = {}
    for log in sample_logs:
        result[(log.source, log.streak_time)] = log.log
    return TimetableSlotLogDict(root=result)

@pytest.fixture
def cache_dir(tmp_path):
    """建立暫存的快取目錄"""
    return tmp_path / "cache"

@pytest.fixture
def cache_with_temp_dir(cache_dir):
    """建立使用暫存目錄的快取實例"""
    cache = TimetableSlotLogCache()
    cache._cache_dir = cache_dir
    cache._cache_file = cache_dir / "timetable_slot_log.json"
    cache._cache_dir.mkdir(exist_ok=True)
    return cache

class TestTimetableSlotLogDict:
    async def test_convert_list_to_dict(self, sample_logs, sample_dict):
        """測試列表轉換為字典格式"""
        cache = TimetableSlotLogCache()
        result = cache._convert_to_dict(sample_logs)
        assert result.root == sample_dict.root

    async def test_fetch_without_cache_creates_new_cache(self):
        """測試沒有提供快取時會建立新的快取實例"""
        result = await TimetableSlotLogDict.fetch()
        assert isinstance(result, TimetableSlotLogDict)

class TestCache:
    async def test_memory_cache(self, cache_with_temp_dir, sample_dict):
        """測試記憶體快取"""
        global _memory_cache
        _memory_cache = None  # 清除記憶體快取
        
        # 儲存到記憶體快取
        await cache_with_temp_dir.save_to_memory(sample_dict)
        
        # 從記憶體快取讀取
        result = await cache_with_temp_dir.fetch_from_memory()
        assert result.root == sample_dict.root

    async def test_file_cache(self, cache_with_temp_dir, sample_logs):
        """測試檔案快取"""
        # 儲存到檔案快取
        await cache_with_temp_dir.save_to_file(sample_logs)
        
        # 從檔案快取讀取
        result = await cache_with_temp_dir.fetch_from_file()
        assert isinstance(result, TimetableSlotLogDict)
        
        # 驗證轉換後的資料是否正確
        expected = cache_with_temp_dir._convert_to_dict(sample_logs)
        assert result.root == expected.root

    async def test_fetch_fallback(self, cache_with_temp_dir, sample_dict, sample_logs):
        """測試快取的 fallback 機制"""
        global _memory_cache
        _memory_cache = None  # 清除記憶體快取
        
        # 第一次fetch：從source取得資料
        result1 = await cache_with_temp_dir.fetch()
        assert isinstance(result1, TimetableSlotLogDict)
        
        # 第二次fetch：應該從記憶體快取取得
        result2 = await cache_with_temp_dir.fetch()
        assert result2 is _memory_cache
        
        # 清除記憶體快取
        _memory_cache = None
        
        # 第三次fetch：應該從檔案快取取得
        result3 = await cache_with_temp_dir.fetch()
        assert isinstance(result3, TimetableSlotLogDict)
        
        # 強制更新
        result4 = await cache_with_temp_dir.fetch(refresh=True)
        assert isinstance(result4, TimetableSlotLogDict)
