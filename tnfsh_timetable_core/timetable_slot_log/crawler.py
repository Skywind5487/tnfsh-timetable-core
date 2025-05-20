import re
from typing import List, Dict, Optional, Tuple
from tnfsh_timetable_core.abc.crawler_abc import BaseCrawlerABC
from tnfsh_timetable_core.timetable.models import CourseInfo, TimeTable
from tnfsh_timetable_core.timetable_slot_log.timetable_slot_log import TimetableSlotLog
from tnfsh_timetable_core.timetable_slot_log.models import StreakTime
from tnfsh_timetable_core.index.index import Index

from tnfsh_timetable_core.index.crawler import reverse_index

from tnfsh_timetable_core.index.models import ReverseIndexResult

class TimetableSlotLogCrawler(
        BaseCrawlerABC[List[CourseInfo]]
    ):
    async def fetch_raw(self, index: Index = None) -> List[TimeTable]:
        if index is None:
            index = Index()
        index.fetch()
        
        reverse_index: ReverseIndexResult = index.reverse_index
        result_list: List[TimeTable] = []
        
        for target in reverse_index.root.keys():
            result_list.append(TimeTable.fetch_cached(target=target))

        return result_list
    
    def parse(self, raw: List[TimeTable]) -> List[TimetableSlotLog]:
        result = []
        for timetable in raw:
            source = getattr(timetable, "target", None)  # 根據你的 TimeTable 結構調整

            for day_index, day in enumerate(timetable.table):
                prev_course: Optional[CourseInfo] = None
                streak = 1
                start_period = 0

                for period_index, course in enumerate(day):

                    if period_index == 0:
                        prev_course = course
                        continue

                    if course == prev_course:
                        streak += 1

                    else:
                        streak_time = StreakTime(
                            weekday=day_index + 1,
                            period=start_period + 1,
                            streak=streak
                        )
                        result.append(TimetableSlotLog(
                            source=source,
                            streak_time=streak_time,
                            log=prev_course
                        ))
                        streak = 1
                        start_period = period_index

                    prev_course = course

                # 處理當天最後一組
                streak_time = StreakTime(
                    weekday=day_index + 1,
                    period=start_period + 1,
                    streak=streak
                )
                result.append(TimetableSlotLog(
                    source=source,
                    streak_time=streak_time,
                    log=prev_course
                ))
        return result

