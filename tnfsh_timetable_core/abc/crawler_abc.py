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

    async def fetch(self, *args, **kwargs) -> T:
        """
        外部統一調用：自動 fetch_raw 並 parse，回傳結構化資料
        """
        raw = await self.fetch_raw(*args, **kwargs)
        return self.parse(raw, *args, **kwargs)