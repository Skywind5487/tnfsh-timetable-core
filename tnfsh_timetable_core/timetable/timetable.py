from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional, Literal, Dict, Tuple
from datetime import datetime, time
from unicodedata import category
from pydantic import BaseModel, Field, computed_field
from functools import cached_property


from tnfsh_timetable_core.utils.logger import get_logger
from tnfsh_timetable_core.timetable.models import CourseInfo
from tnfsh_timetable_core.abc.domain_abc import BaseDomainABC
if TYPE_CHECKING:
    from tnfsh_timetable_core.timetable.models import TimetableSchema

# 設定日誌
logger = get_logger(logger_level="INFO")

# 定義型別別名
TimeInfo = Tuple[str, str]
PeriodName = str
class Timetable(BaseDomainABC, BaseModel):
    """學校課表的資料結構
    
    代表一份完整的課表，包含：
    - 5x8 的課程矩陣（週一到週五，每天8節）
    - 課表類型（班級/教師）
    - 目標資訊（班級編號或教師姓名）
    - 原始網頁路徑
    - 課表時間資訊
    - 午休課程資訊
    - 快取抓取時間
    """

    # 識別資訊
    target: str
    category: str | None = None  # 分類名稱（如 "國文科"）
    target_url: str
    role: Literal["class", "teacher"]
    id: str
    
    # 更新資訊
    last_update: datetime  # 遠端更新時間
    cache_fetch_at: datetime | None = None  # 快取抓取時間
    
    # 核心資料
    table: List[List[Optional[CourseInfo]]]  # 5 weekdays x 8 periods
    periods: Dict[
        str, # 節次名稱（如 "第一節"）
        Tuple[
            time, # 節次開始時間
            time # 節次結束時間
        ]
    ]  # 節次時間資訊 
    lunch_break: List[Optional[CourseInfo]] | None = None  # 午休課程資訊 5 weekdays
    lunch_break_periods: Dict[
        str,
        Tuple[time, time]
    ] | None = None  # 午休時間資訊，格式同 periods

    
    
    
    
    def determine_role(cls, target: str) -> Literal["class", "teacher"]:
        """根據目標名稱判斷課表角色
        這裡使用簡單的規則：如果是純數字則為班級，否則為教師
        使用簡單的規則：如果是純數字則為班級，否則為教師
        
        Args:
            target: 目標名稱（班級或教師）
            
        Returns:
            Literal["class", "teacher"]: 課表類型
        """
        return "class" if target.isdigit() else "teacher"
    
    @classmethod
    def from_schema(cls, schema: "TimetableSchema", cache_fetch_at: datetime | None = None) -> "Timetable":
        # 轉換 periods: Dict[str, Tuple[str, str]] → Dict[str, Tuple[time, time]]
        periods: Dict[str, Tuple[time, time]] = {
            name: (
                time.fromisoformat(start),
                time.fromisoformat(end)
            )
            for name, (start, end) in schema.periods.items()
        }
        # 轉換午休時間
        lunch_break_periods = None
        if schema.lunch_break_periods:
            lunch_break_periods = {
                name: (
                    time.fromisoformat(start),
                    time.fromisoformat(end)
                )
                for name, (start, end) in schema.lunch_break_periods.items()
            }
        # 轉換 last_update: str → datetime
        last_update = schema.last_update_datetime
        return cls(
            target=schema.target,
            category=schema.category,
            target_url=schema.target_url,
            role=schema.role,
            id=schema.id,
            last_update=last_update,
            cache_fetch_at=cache_fetch_at,
            table=schema.table,
            periods=periods, # datetime.time 格式
            lunch_break=schema.lunch_break,
            lunch_break_periods=lunch_break_periods, # datetime.time 格式
        )
    
    @classmethod
    async def fetch(cls, target: str, refresh: bool = False) -> Timetable:
        """
        支援三層快取的智能載入方法：
        1. 記憶體 → 2. 本地檔案 → 3. 網路請求（可透過 refresh 強制重新建立）
        並在 refresh 時同步更新記憶體與本地快取。

        Args:
            target: 目標名稱（班級或教師）
            refresh: 是否強制從網路重新獲取
            
        Returns:
            Timetable: 課表資料實例
        """
        from tnfsh_timetable_core.timetable.cache import TimeTableCache
        # 使用快取系統來獲取課表資料
        cache = TimeTableCache()
        instance = await cache.fetch(target, refresh=refresh)
        return cls.from_schema(instance.data, cache_fetch_at=instance.metadata.cache_fetch_at)


    def export_calendar(
        self, 
        type: Literal["csv", "ics"], 
        filepath: Optional[str] = None,
        has_a_href: bool = True,
        location: Optional[str] = None,
    ) -> str:
        """
        將課表資料匯出為指定格式的檔案（僅作為接口，實作委派給外部函式）
        returns:
            str: 實際儲存的檔案路徑
        """
        from tnfsh_timetable_core.timetable.export_calendar import export_calendar
        return export_calendar(
            self, 
            type=type, 
            filepath=filepath, 
            has_a_href=has_a_href,
            location=location,
        )

if __name__ == "__main__":
    # 測試用例
    import asyncio
    async def main():
        target = "陳暐捷"
        timetable = await Timetable.fetch(target, refresh=True)
        timetable.export_calendar(
            type="csv",
            filepath=f"{target}_timetable.csv"
        )
    asyncio.run(main())