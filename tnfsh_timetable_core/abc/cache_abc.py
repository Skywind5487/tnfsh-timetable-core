from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseCacheABC(ABC):
    """
    Cache 層的抽象基底類，規範三層快取（memory/file/source）的標準介面。

    推薦 fetch fallback/save 流程：
    1. 先嘗試 fetch_from_memory，若有資料直接回傳。
    2. 若 memory 沒有，則 fetch_from_file，若有資料則 save_to_memory 並回傳。
    3. 若 file 也沒有，則 fetch_from_source，然後 save_to_file、save_to_memory，最後回傳。
    4. 具體流程建議由子類在 fetch 方法中實作。
    """

    @abstractmethod
    async def fetch(self, *args, refresh: bool = False, **kwargs) -> Any:
        """統一對外取得資料（自動處理 memory/file/source）"""
        pass

    @abstractmethod
    async def fetch_from_memory(self, *args, **kwargs) -> Optional[Any]:
        """從記憶體快取取得資料"""
        pass

    @abstractmethod
    async def fetch_from_file(self, *args, **kwargs) -> Optional[Any]:
        """從本地檔案快取取得資料"""
        pass

    @abstractmethod
    async def fetch_from_source(self, *args, **kwargs) -> Any:
        """從最終來源取得資料（如網路、其他服務等）"""
        pass

    @abstractmethod
    async def save_to_memory(self, data: Any, *args, **kwargs) -> None:
        """儲存資料到記憶體快取"""
        pass

    @abstractmethod
    async def save_to_file(self, data: Any, *args, **kwargs) -> None:
        """儲存資料到本地檔案快取"""
        pass
