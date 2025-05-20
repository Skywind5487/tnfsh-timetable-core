from abc import ABC, abstractmethod
from typing import Any

class BaseCrawlerABC(ABC):
    """
    Crawler 層的抽象基底類，規範所有爬蟲/資料抓取器的標準介面。
    """
    @abstractmethod
    async def fetch_raw(self, *args, **kwargs) -> Any:
        """抓取原始資料（如 HTML、API 回傳等）"""
        pass

    @abstractmethod
    def parse(self, raw: Any, *args, **kwargs) -> Any:
        """解析原始資料為結構化資料"""
        pass
