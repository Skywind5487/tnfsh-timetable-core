import pytest
import pytest_asyncio
from pathlib import Path
from tnfsh_timetable_core.timetable_slot_log_dict.cache import TimetableSlotLogCache, _memory_cache
from tnfsh_timetable_core.timetable_slot_log_dict.models import TimetableSlotLog, StreakTime
from tnfsh_timetable_core.timetable_slot_log_dict.timetable_slot_log_dict import TimetableSlotLogDict
from tnfsh_timetable_core.timetable.models import CourseInfo

@pytest_asyncio.fixture
async def sample_logs():
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

@pytest_asyncio.fixture
async def sample_dict(sample_logs):
    """將測試資料轉換為字典格式"""
    result = {}
    for log in sample_logs:
        result[(log.source, log.streak_time)] = log.log
    return TimetableSlotLogDict(root=result)

@pytest_asyncio.fixture
async def cache_dir(tmp_path):
    """建立暫存的快取目錄"""
    return tmp_path / "cache"

@pytest_asyncio.fixture
async def cache_with_temp_dir(cache_dir):
    """建立使用暫存目錄的快取實例"""
    cache = TimetableSlotLogCache()
    cache._cache_dir = cache_dir
    cache._cache_file = cache_dir / "timetable_slot_log.json"
    cache._cache_dir.mkdir(exist_ok=True)
    return cache

class TestTimetableSlotLogDict:
    @pytest.mark.asyncio
    async def test_convert_list_to_dict(self, sample_logs, sample_dict):
        """測試列表轉換為字典格式"""
        cache = TimetableSlotLogCache()
        result = cache._convert_to_dict(sample_logs)
        assert result.root == sample_dict.root

    @pytest.mark.asyncio
    async def test_fetch_without_cache_creates_new_cache(self):
        """測試沒有提供快取時會建立新的快取實例"""
        result = await TimetableSlotLogDict.fetch()
        assert isinstance(result, TimetableSlotLogDict)

class TestCache:
    @pytest.mark.asyncio
    async def test_memory_cache(self, cache_with_temp_dir, sample_dict):
        """測試記憶體快取"""
        global _memory_cache
        _memory_cache = None  # 清除記憶體快取
        
        cache = cache_with_temp_dir
        dict_result = sample_dict
        
        # 儲存到記憶體快取
        await cache.save_to_memory(dict_result)
        
        # 從記憶體快取讀取
        result = await cache.fetch_from_memory()
        assert result.root == dict_result.root

    @pytest.mark.asyncio
    async def test_file_cache(self, cache_with_temp_dir, sample_logs):
        """測試檔案快取"""
        cache = cache_with_temp_dir
        logs = sample_logs
        
        # 儲存到檔案快取
        await cache.save_to_file(logs)
        
        # 從檔案快取讀取
        result = await cache.fetch_from_file()
        assert isinstance(result, TimetableSlotLogDict)
        
        # 驗證轉換後的資料是否正確
        expected = cache._convert_to_dict(logs)
        assert result.root == expected.root

    @pytest.mark.asyncio
    async def test_fetch_fallback(self, cache_with_temp_dir, sample_dict, sample_logs):
        """測試快取的 fallback 機制"""
        from tnfsh_timetable_core.timetable_slot_log_dict import cache as ch
        ch._memory_cache = None  # 清除記憶體快取

        from tnfsh_timetable_core.timetable_slot_log_dict.cache import TimetableSlotLogCache 
        cache: TimetableSlotLogCache = cache_with_temp_dir
        logs = sample_logs
        dict_result = sample_dict
        
        # 第一次fetch：從source取得資料
        result1 = await cache.fetch()
        assert isinstance(result1, TimetableSlotLogDict)
        
    
        # 第二次fetch：應該從記憶體快取取得
        result2 = await cache.fetch()
        assert result2 is ch._memory_cache
        
        # 清除記憶體快取
        ch._memory_cache = None

        # 第三次fetch：應該從檔案快取取得
        result3 = await cache.fetch()
        assert isinstance(result3, TimetableSlotLogDict)
        
        # 強制更新
        result4 = await cache.fetch(refresh=True)
        assert isinstance(result4, TimetableSlotLogDict)
