from __future__ import annotations
"""台南一中課表系統核心模組"""
from typing import TYPE_CHECKING, List, Optional
if TYPE_CHECKING:
    from tnfsh_timetable_core.timetable.models import TimeTable
    from tnfsh_timetable_core.index.index import Index
    from tnfsh_timetable_core.scheduling.scheduling import Scheduling

class TNFSHTimetableCore:
    """台南一中課表核心功能的統一入口點
    
    此類別提供以下功能：
    1. 課表相關操作
       - get_timetable(): 取得課表物件
       - fetch_timetable(): 從網路獲取課表資料
       
    2. 索引相關操作
       - get_index(): 取得索引物件
       - fetch_index(): 從網路獲取索引資料
       
    3. 課表時段紀錄
       - get_timetable_slot_log_dict(): 取得課表時段紀錄物件
       - fetch_timetable_slot_log_dict(): 從網路獲取課表時段紀錄
       
    4. 排課演算法
       - scheduling_rotation(): 執行課程輪調搜尋
       - scheduling_swap(): 執行課程交換搜尋
    """
    
    # deprecated
    async def fetch_timetable(self, target: str, refresh: bool = False):
        """從網路獲取課表資料
        
        Args:
            target: 目標課表，例如 "class_307" 或 "teacher_john"
            refresh: 是否強制重新抓取，預設為 False
            
        Returns:
            TimeTable: 包含課表資料的物件
        """
        from tnfsh_timetable_core.timetable.models import TimeTable        
        return await TimeTable.fetch_cached(target=target, refresh=refresh)

    async def fetch_index(self)-> Index:
        """從網路獲取索引資料
        
        Returns:
            Index: 包含最新索引資料的物件
        """
        from tnfsh_timetable_core.index.index import Index
        index = Index()
        await index.fetch()
        return index
    
    async def fetch_timetable_slot_log_dict(self, refresh: bool = False):
        """從網路獲取課表時段紀錄

        Returns:
            TimetableSlotLogDict: 包含最新課表時段紀錄的物件
        """
        from tnfsh_timetable_core.timetable_slot_log_dict.timetable_slot_log_dict import TimetableSlotLogDict
        timetable_slot_log_dict = await TimetableSlotLogDict.fetch(refresh=refresh)
        return timetable_slot_log_dict

    async def fetch_scheduling(self) -> Scheduling:
        """取得排課物件
        
        Returns:
            Scheduling: 排課物件實例
        """
        from tnfsh_timetable_core.scheduling.scheduling import Scheduling
        return Scheduling()

    async def scheduling_rotation(self, teacher_name: str, weekday: int, period: int, max_depth: int = 3):
        """執行課程輪調搜尋
        
        搜尋指定教師在特定時段的所有可能輪調路徑。
        
        Args:
            teacher_name: 教師名稱
            weekday: 星期幾 (1-5)
            period: 第幾節 (1-8)
            max_depth: 最大搜尋深度，預設為 3。較大的深度會找到更長的輪調路徑，但也會增加搜尋時間
            
        Returns:
            list: 所有找到的輪調路徑
            
        Raises:
            ValueError: 當 weekday 不在 1-5 之間或 period 不在 1-8 之間時
        """
        from tnfsh_timetable_core.scheduling.scheduling import Scheduling
        scheduling = Scheduling()
        return await scheduling.rotation(teacher_name=teacher_name, weekday=weekday, period=period, max_depth=max_depth)

    async def scheduling_swap(self, teacher_name: str, weekday: int, period: int, max_depth: int = 3):
        """執行課程交換搜尋
        
        搜尋指定教師在特定時段的所有可能交換路徑。
        
        Args:
            teacher_name: 教師名稱
            weekday: 星期幾 (1-5)
            period: 第幾節 (1-8)
            max_depth: 最大搜尋深度，預設為 3。較大的深度會找到更長的交換路徑，但也會增加搜尋時間
            
        Returns:
            list: 所有找到的交換路徑
            
        Raises:
            ValueError: 當 weekday 不在 1-5 之間或 period 不在 1-8 之間時
        """
        from tnfsh_timetable_core.scheduling.scheduling import Scheduling
        scheduling = Scheduling()
        return await scheduling.swap(teacher_name=teacher_name, weekday=weekday, period=period, max_depth=max_depth)
