from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic

T = TypeVar("T")

class BaseCrawlerABC(ABC, Generic[T]):
    """
    Crawler 層的抽象基底類，規範所有爬蟲/資料抓取器的標準介面。
    """
    @abstractmethod
    async def fetch_raw(self, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    def parse(self, raw: Any, *args, **kwargs) -> T:
        pass
    
    @abstractmethod
    async def fetch(self, *args, **kwargs) -> T:
        pass