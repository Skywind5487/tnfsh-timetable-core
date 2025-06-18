from __future__ import annotations
from typing import List, Optional, Dict, Tuple, Literal
from datetime import datetime
from pydantic import BaseModel, Field

# 基礎型別定義
TimeInfo = Tuple[str, str]  # (開始時間, 結束時間) e.g. ("08:00", "08:50")

class FetchError(Exception):
    """爬取課表時可能發生的錯誤"""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class CounterPart(BaseModel):
    """參與者（老師或班級）的資訊"""
    participant: str  # 參與者名稱
    url: str         # 參與者的課表連結

class CourseInfo(BaseModel):
    """課程資訊
    
    包含：
    - 科目名稱
    - 對應的參與者（老師教的是哪個班，或班級上的是哪個老師）
    """
    subject: str
    counterpart: Optional[List[CounterPart]] = None

class TimetableSchema(BaseModel):
    """學校課表的資料結構
    
    代表一份完整的課表，包含：
    - 5x8 的課程矩陣（週一到週五，每天8節）
    - 節次時間對照表
    - 課表基本資訊（類型、目標、更新時間等）
    """
    # 核心資料
    table: List[List[Optional[CourseInfo]]]  # 5 weekdays x 8 periods
    periods: Dict[str, TimeInfo]  # 課表時間資訊 {第一節: ("08:00", "09:30"), ...}

    # 識別資訊
    type: Literal["class", "teacher"]
    target: str
    target_url: str
    
    # 更新資訊
    last_update: str  # 遠端更新時間

class CacheMetadata(BaseModel):
    """快取的元數據，記錄資料的生命週期資訊"""
    cache_fetch_at: datetime = Field(description="資料從遠端抓取的時間")

class CachedTimeTable(BaseModel):
    """完整的課表快取結構
    
    包含：
    1. metadata: 快取的元數據（時間戳記）
    2. data: 實際的課表資料（TimetableSchema）
    """
    metadata: CacheMetadata
    data: TimetableSchema


