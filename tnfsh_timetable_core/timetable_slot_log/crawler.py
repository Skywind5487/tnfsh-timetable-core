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
        
    def parse(self, raw: List[TimeTable]) -> TimetableSlotLog:
        result: TimetableSlotLog = {}

        for timetable in raw:
            for day_index, day in enumerate(timetable.table):
                streak: int = 1
                prev_course: Optional[CourseInfo] = None
                for period_index, course in enumerate(day):
                    if period_index == 0:
                        prev_course = course
                        continue
                    
                    if course == prev_course:
                        streak += 1
                        if period_index == len(day) - 1:
                            result[
                                (timetable.target), 
                                StreakTime(
                                    weekday = day + 1,
                                    period = period_index - 1 + 1, # -1 代表紀錄上一個
                                    streak = streak + 1
                                )
                            ] = course  
                        continue
                    
                    
                        

                    result[
                        (timetable.target), 
                        StreakTime(
                            weekday = day + 1,
                            period = period_index - 1 + 1, # -1 代表紀錄上一個
                            streak = streak
                        )
                    ] = course
                    prev_course = course
                    streak = 1


                
