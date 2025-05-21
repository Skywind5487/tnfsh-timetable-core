import re
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from tnfsh_timetable_core.abc.crawler_abc import BaseCrawlerABC
from tnfsh_timetable_core.timetable_slot_log_dict.models import StreakTime, TimetableSlotLog

if TYPE_CHECKING:
    from tnfsh_timetable_core.timetable.models import CourseInfo, TimeTable
    from tnfsh_timetable_core.index.index import Index
    from tnfsh_timetable_core.index.models import ReverseIndexResult

class TimetableSlotLogCrawler(
    BaseCrawlerABC[List["CourseInfo"]]
):
        
    async def fetch_raw(self, index: "Index" = None) -> List["TimeTable"]:
        if index is None:
            from tnfsh_timetable_core.index.index import Index
            index = Index()
        await index.fetch()
        
        from tnfsh_timetable_core.index.models import ReverseIndexResult
        reverse_index: ReverseIndexResult = index.reverse_index
        result_list: List["TimeTable"] = []
        
        from tnfsh_timetable_core.timetable.models import TimeTable
        for target in reverse_index.root.keys():
            result_list.append(await TimeTable.fetch_cached(target=target))

        return result_list

    def parse(self, raw: List["TimeTable"]) -> List[TimetableSlotLog]:
        # 動態引入，避免循環引用
        from tnfsh_timetable_core.timetable.models import CourseInfo
        
        result = []
        for timetable in raw:
            source = getattr(timetable, "target", None)

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
                        
                        result.append(
                            TimetableSlotLog(
                                source=source,
                                streak_time=streak_time,
                                log=prev_course
                            )
                        )

                        prev_course = course
                        start_period = period_index
                        streak = 1
                        
                # 處理每天最後一筆資料
                streak_time = StreakTime(
                    weekday=day_index + 1,
                    period=start_period + 1,
                    streak=streak
                )
                result.append(
                    TimetableSlotLog(
                        source=source,
                        streak_time=streak_time,
                        log=prev_course
                    )
                )

        return result

    async def fetch(self, index = None) -> List[TimetableSlotLog]:
        raw_data = await self.fetch_raw(index=index)
        return self.parse(raw_data)

