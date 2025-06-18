from abc import ABC, abstractmethod
from typing import Any

class BaseDomainABC(ABC):
    """
    Domain 層的抽象基底類，規範所有核心資料結構（業務模型）的標準介面。
    建議用於：Timetable、CourseInfo、OriginLog、TeacherNode、ClassNode 等。
    
    """
    @classmethod
    @abstractmethod
    async def fetch(cls, *args, refresh: bool = False, **kwargs):
        """
        回傳子類本身
        如果 refresh=True，要logger info出來。
        
        Args:
            refresh (bool, optional)
        """
        pass
