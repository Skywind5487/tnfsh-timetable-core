from __future__ import annotations
from typing import List, Dict, TypeAlias, Optional, Any, Literal, ClassVar
from datetime import datetime
import json
from pydantic import BaseModel
from tnfsh_timetable_core.timetable.crawler import RawParsedResult
from tnfsh_timetable_core.utils.logger import get_logger

# 設定日誌
logger = get_logger(logger_level="INFO")


class ScheduleEntry(BaseModel):
    weekday: int   # 1–5 (Mon–Fri)
    period: int    # 1–8
    subject: str
    teacher: str
    class_code: str


TimeSlot: TypeAlias = tuple[int, int]  # (weekday, period)

class Lookup(BaseModel):
    """
    用兩層 dict 取代複雜 SQL：
    - teacher_lookup[teacher][(weekday, period)] = ScheduleEntry
    - class_lookup[class_code][(weekday, period)] = ScheduleEntry
    """
    teacher_lookup: Dict[str, Dict[TimeSlot, ScheduleEntry]]
    class_lookup:  Dict[str, Dict[TimeSlot, ScheduleEntry]]
    last_update:   datetime  # 嚴格格式：%Y/%m/%d %H:%M:%S

class CounterPart(BaseModel):
    participant: str
    url: str

class CourseInfo(BaseModel):
    subject: str
    main: str # name of the class or teacher
    counterpart: Optional[List[CounterPart]] # name of the class or teacher


class TimeTable(BaseModel):
    table: List[List[Optional[CourseInfo]]]  # 5 weekdays x 8 periods
    type: Literal["class", "teacher"]
    target: str
    target_url: str  

    @classmethod
    async def from_parsed(cls, target: str, parsed: RawParsedResult) -> "TimeTable":
        # TNFSHClassTableIndex 已經在文件頂部導入
        from tnfsh_timetable_core import TNFSHTimetableCore
        core = TNFSHTimetableCore()
        index = core.fetch_index()
        await index.fetch()
        
        reverse_index = index.reverse_index
        target_url = reverse_index[target]["url"]
        type_ = "class" if target.isdigit() else "teacher"

        # ✅ 新增：轉置 parsed["table"] → weekday-major
        raw_table = parsed["table"]  # shape: [period][weekday]
        rotated_table = list(map(list, zip(*raw_table)))  # shape: [weekday][period]

        table: List[List[Optional[CourseInfo]]] = []

        for row in rotated_table:  # ✅ 改成處理轉置後的 row
            parsed_row: List[Optional[CourseInfo]] = []
            for cell in row:
                if not cell or cell == {"": {"": ""}}:
                    parsed_row.append(None)
                    continue

                subject = next(iter(cell))
                teachers_or_classes = cell[subject]  # Dict[name, url]

                # Prepare counterpart list
                counterpart_list = [
                    CounterPart(participant=name, url=url)
                    for name, url in teachers_or_classes.items()
                    if url and url != target_url
                ]

                # 判斷主體名稱
                main_name = target
                for name, url in teachers_or_classes.items():
                    if url == target_url:
                        main_name = name
                        break

                parsed_row.append(CourseInfo(
                    subject=subject,
                    main=main_name,
                    counterpart=counterpart_list if counterpart_list else None
                ))
            table.append(parsed_row)

        return cls(
            table=table,
            type=type_,
            target=target,
            target_url=target_url
        )    
    
    @classmethod
    async def fetch_cached(cls, target: str, refresh: bool = False) -> "TimeTable":
        """
        支援三層快取的智能載入方法：
        1. 記憶體 → 2. 本地檔案 → 3. 網路請求（可透過 refresh 強制重新建立）
        並在 refresh 時同步更新記憶體與本地快取。
        """
        from tnfsh_timetable_core.timetable.cache import prebuilt_cache, load_from_disk, save_to_disk

        key = target

        # 層 1：記憶體
        if not refresh and key in prebuilt_cache:
            logger.debug(f"✨ 從記憶體快取取得課表：{target}")
            return prebuilt_cache[key]

        # 層 2：本地 JSON
        if not refresh:
            logger.debug(f"💾 嘗試從本地快取載入：{target}")
            data = load_from_disk(target)
            if data:
                try:
                    # 嘗試從 JSON 載入資料
                    instance = cls.model_validate(data)
                    prebuilt_cache[key] = instance
                    logger.debug(f"📥 成功從本地快取載入：{target}")
                    return instance
                except Exception as e:
                    logger.error(f"❌ 本地快取資料無效：{target}，錯誤：{e}")

        # 層 3：fallback → 網路 request
        logger.info(f"🌐 從網路抓取課表資料：{target}")
        instance = await cls._request(target)

        # 同步更新兩層 cache
        prebuilt_cache[key] = instance
        save_to_disk(target, instance)
        logger.debug(f"💾 已更新快取：{target}")

        return instance    
    
    @classmethod
    async def _request(cls, target: str) -> "TimeTable":
        """從網路抓取課表資料。"""
        from tnfsh_timetable_core.timetable.crawler import fetch_raw_html, parse_html
        try:
            logger.debug(f"📡 正在抓取課表頁面：{target}")
            soup = await fetch_raw_html(target)
            logger.debug(f"🔍 解析課表資料：{target}")
            parsed = parse_html(soup)
            logger.debug(f"✅ 課表資料解析完成：{target}")
            return await cls.from_parsed(target, parsed)
        except Exception as e:
            logger.error(f"❌ 抓取課表失敗：{target}，錯誤：{e}")
            raise

if __name__ == "__main__":
    # For test cases, see: tests/test_timetable/test_models.py
    pass