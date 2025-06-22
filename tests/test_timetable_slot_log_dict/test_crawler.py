from annotated_types import T
from typing import List
import pytest

class DummyTimeTable:
    def __init__(self, target, table):
        self.target = target
        self.table = table

def test_parse_slotlog_basic():
    from tnfsh_timetable_core.timetable.timetable import Timetable, CourseInfo
    from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime
    # 模擬一個班級有三天，每天三節課
    # 第一天：A, A, None（2連堂A+1空堂）
    # 第二天：B, B, B（3連堂B）
    # 第三天：None, None, C（2連空+1單堂C）
    A = CourseInfo(subject="A")
    B = CourseInfo(subject="B")
    C = CourseInfo(subject="C")
    timetable = DummyTimeTable(
        target="class_001",
        table=[
            [A, A, None],
            [B, B, B],
            [None, None, C]
        ]
    )
    
    from tnfsh_timetable_core.timetable_slot_log_dict.models import TimetableSlotLog
    from tnfsh_timetable_core.timetable_slot_log_dict.crawler import TimetableSlotLogCrawler
    crawler = TimetableSlotLogCrawler()
    slotlog: List[TimetableSlotLog] = crawler.parse([timetable])
    for log in slotlog:
        json =log.model_dump_json(indent=4)
        print(json)
        # 預期的 slotlog 結果
    expected = [
        # 第一天
        TimetableSlotLog(source="class_001", streak_time=StreakTime(weekday=1, period=1, streak=2), log=A),
        TimetableSlotLog(source="class_001", streak_time=StreakTime(weekday=1, period=3, streak=1), log=None),#
        # 第二天
        TimetableSlotLog(source="class_001", streak_time=StreakTime(weekday=2, period=1, streak=3), log=B),
        # 第三天
        TimetableSlotLog(source="class_001", streak_time=StreakTime(weekday=3, period=1, streak=2), log=None),
        TimetableSlotLog(source="class_001", streak_time=StreakTime(weekday=3, period=3, streak=1), log=C),
    ]
    
    # 驗證每個結果都在 slotlog 中
    for expected_log in expected:
        assert expected_log in slotlog

if __name__ == "__main__":
    test_parse_slotlog_basic()