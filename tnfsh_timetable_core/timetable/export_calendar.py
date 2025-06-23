from __future__ import annotations
from typing import Literal, Optional, Generator, Dict, Any
from tnfsh_timetable_core.timetable.timetable import Timetable
from tnfsh_timetable_core.timetable.models import CourseInfo, TimetableSlot
from tnfsh_timetable_core import TNFSHTimetableCore
core = TNFSHTimetableCore()
logger = core.get_logger(logger_level="DEBUG")
DEFAULT_LOCATION = "701台南市東區民族路一段1號"

def get_weeks(today, monday) -> int:
    """
    計算本學期剩餘週數。
    """
    if today.month >= 8:
        target_date = today.replace(year=today.year + 1, month=2, day=1)
    else:
        target_date = today.replace(month=7, day=1)
    return ((target_date - monday).days // 7) + 1

def get_repeat_rule(weeks: int, weekday: int) -> dict:
    """
    產生 icalendar 標準的 repeat 規則 dict，適用於 ics 也可轉為 csv 字串。
    """
    weekday_map = {0: 'MO', 1: 'TU', 2: 'WE', 3: 'TH', 4: 'FR'}
    return {
        'freq': 'weekly',
        'count': weeks,
        'byday': [weekday_map[weekday]],
        'wkst': 'MO'
    }

def to_csv_repeat_rule(repeat_dict: dict) -> str:
    """
    將 repeat dict 轉為 icalendar 字串格式，供 csv 使用。
    """
    return (
        f"FREQ={repeat_dict['freq'].upper()};"
        f"COUNT={repeat_dict['count']};"
        f"BYDAY={','.join(repeat_dict['byday'])};"
        f"WKST={repeat_dict['wkst']}"
    )

def export_calendar(
    timetable: Timetable,
    type: Literal["csv", "ics"],
    filepath: Optional[str] = None,
    has_a_href: bool = True,
    location: str = DEFAULT_LOCATION
) -> str:
    if type == "csv":
        return _export_to_csv(timetable, filepath, has_a_href=has_a_href, location=location)
    elif type == "ics":
        return _export_to_ics(timetable, filepath, has_a_href=has_a_href, location=location)
    else:
        raise ValueError(f"不支援的匯出格式: {type}")

def iter_timetable_slots(
    timetable: Timetable
) -> Generator[TimetableSlot, None, None]:
    """
    Generator: 依序產生每個課表時段的 TimetableSlot 實例。
    僅保留匯出/下游實際需要的欄位（weekday, course, start_datetime, end_datetime）。
    """
    from datetime import timedelta, date, datetime
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    period_names = list(timetable.periods.keys())
    for weekday, lessons in enumerate(timetable.table):
        for period_idx, course in enumerate(lessons):
            if not course:
                continue
            start_time, end_time = (
                timetable.periods[
                    period_names[period_idx]
                ]
            )
            current_date = monday + timedelta(days=weekday)
            start_datetime = datetime.combine(current_date, start_time)
            end_datetime = datetime.combine(current_date, end_time)
            yield TimetableSlot(
                weekday=weekday,
                course=course,
                start_datetime=start_datetime,
                end_datetime=end_datetime
            )
    if timetable.lunch_break and timetable.lunch_break_periods:
        # 處理午休課程
        lunch_break_periods = timetable.lunch_break_periods
        for weekday, course in enumerate(timetable.lunch_break):
            if not course:
                continue
            start_time, end_time = lunch_break_periods["午休"]
            current_date = monday + timedelta(days=weekday)
            start_datetime = datetime.combine(current_date, start_time)
            end_datetime = datetime.combine(current_date, end_time)
            yield TimetableSlot(
                weekday=weekday,
                course=course,
                start_datetime=start_datetime,
                end_datetime=end_datetime
            )


def _export_to_csv(
    timetable: Timetable,
    filepath: Optional[str] = None,
    has_a_href: bool = True,
    location: str = DEFAULT_LOCATION
) -> str:
    import csv
    from datetime import date, timedelta
    if filepath is None:
        filepath = f"{timetable.role}_{timetable.target}.csv"
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            "Subject",
            "Start Date",
            "Start Time",
            "End Time",
            "Description",
            "Location",
            "Repeat"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        weeks = get_weeks(today, monday)
        for slot in iter_timetable_slots(timetable):
            repeat_dict = get_repeat_rule(weeks, slot.weekday)
            repeat_rule = to_csv_repeat_rule(repeat_dict)
            writer.writerow({
                "Subject": slot.course.subject,
                "Start Date": slot.start_datetime.strftime("%m/%d/%Y"),
                "Start Time": slot.start_datetime.strftime("%H:%M"),
                "End Time": slot.end_datetime.strftime("%H:%M"),
                "Description": _get_event_description(timetable, slot.course, has_a_href=has_a_href),
                "Location": location,
                "Repeat": repeat_rule
            })
    return filepath

def _export_to_ics(
    timetable: Timetable,
    filepath: Optional[str] = None,
    has_a_href: bool = True,
    location: str = DEFAULT_LOCATION
) -> str:
    from datetime import date, timedelta
    from icalendar import Calendar, Event
    if filepath is None:
        filepath = f"{timetable.role}_{timetable.target}.ics"
    cal = Calendar()
    cal.add('prodid', f'-//{filepath}_台南一中課表//TW')
    cal.add('version', '2.0')
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    weeks = get_weeks(today, monday)
    for slot in iter_timetable_slots(timetable):
        event = Event()
        event.add('summary', slot.course.subject)
        event.add('dtstart', slot.start_datetime)
        event.add('dtend', slot.end_datetime)
        event.add('location', location)
        event.add('description', _get_event_description(timetable, slot.course, has_a_href=has_a_href))
        repeat_dict = get_repeat_rule(weeks, slot.weekday)
        event.add('rrule', repeat_dict)
        cal.add_component(event)
    with open(filepath, 'wb') as f:
        f.write(cal.to_ical())
    return filepath

def _get_event_description(
    timetable: Timetable,
    course_info: Optional[CourseInfo],
    has_a_href: bool = True
) -> str:
    from tnfsh_wiki_teachers_core import TNFSHWikiTeachersCore
    wiki_core = TNFSHWikiTeachersCore()
    wiki_core.fetch_index()
    description = []
    base_url = "http://w3.tnfsh.tn.edu.tw/deanofstudies/course/"
    tnfsh_official_url = "https://www.tnfsh.tn.edu.tw"
    tnfsh_lesson_information_url = "https://www.tnfsh.tn.edu.tw/latestevent/index.aspx?Parser=22,4,25"
    def _get_a_href(url: str, text: str) -> str:
        return f"<a href='{url}'>{text}</a>" if has_a_href else f"{text}({url})"
    if course_info and getattr(course_info, 'counterpart', None):
        links = []
        for cp in course_info.counterpart:
            if cp.url:
                links.append(_get_a_href(base_url + cp.url, cp.participant))
            else:
                links.append(cp.participant)
        description.append(f"對象：{'、'.join(links)}")
    description.append(f"課表連結：{_get_a_href(base_url + timetable.target_url, f'{timetable.target}-課表')}")
    logger.debug(f"課表連結：{base_url + timetable.target_url}")
    
    description.append(f"南一中官網：{_get_a_href(tnfsh_official_url, '南一中官網')}")
    description.append(f"南一中官網-課程資訊：{_get_a_href(tnfsh_lesson_information_url, '教學進度、總體計畫、多元選修等等')}")
    return "\n".join(description)
