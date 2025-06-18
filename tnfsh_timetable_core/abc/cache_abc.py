import json
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseCacheABC(ABC):
    """
    Cache 層的抽象基底類，規範三層快取（memory/file/source）的標準介面。
    """

    @abstractmethod
    async def fetch(self, *args, refresh: bool = False, **kwargs) -> Any:
        """統一對外取得資料（自動處理 memory/file/source）
        
        Args:
            refresh (bool, optional): 是否強制更新快取。若為True，將略過記憶體和檔案快取。
            *args: 傳遞給各層級fetch方法的位置參數
            **kwargs: 傳遞給各層級fetch方法的關鍵字參數

        Returns:
            Any: 取得的資料

        流程：
        1. 如果 refresh=False：
           a. 先嘗試從記憶體快取取得（fetch_from_memory）
           b. 若記憶體無資料，嘗試從檔案快取取得（fetch_from_file）
           c. 取得檔案資料後存入記憶體（save_to_memory）
        2. 如果記憶體和檔案都沒有資料，或 refresh=True：
           a. 從來源取得資料（fetch_from_source）
           b. 將資料儲存到檔案（save_to_file）
           c.將資料儲存到記憶體（save_to_memory）
        3. 返回資料
        """
        # 除非強制更新，否則先嘗試從快取取得
        if not refresh:
            # 嘗試從記憶體取得
            data = await self.fetch_from_memory(*args, **kwargs)
            if data is not None:
                return data
            
            # 嘗試從檔案取得
            data = await self.fetch_from_file(*args, **kwargs)
            if data is not None:
                # 將檔案資料存入記憶體
                await self.save_to_memory(data, *args, **kwargs)
                return data
        
        # 從來源取得資料
        data = await self.fetch_from_source(*args, **kwargs)
        
        # 將資料儲存到檔案和記憶體
        await self.save_to_file(data, *args, **kwargs)
        await self.save_to_memory(data, *args, **kwargs)
        
        return data

    @abstractmethod
    async def fetch_from_memory(self, *args, **kwargs) -> Optional[Any]:
        """從全域變數快取取得資料"""
        pass

    @abstractmethod
    async def save_to_memory(self, data: Any, *args, **kwargs) -> None:
        """儲存資料到全域變數快取"""
        pass

    async def fetch_from_file(self, filepath: str, *args, **kwargs) -> Optional[Any]:
        """從本地檔案快取取得資料
        
        Args:
            filepath (str): JSON檔案的路徑
            *args: 額外的位置參數
            **kwargs: 額外的關鍵字參數
            
        Returns:
            Optional[Any]: 從檔案讀取的資料，如果檔案不存在或讀取失敗則返回None
        """
        try:
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
            print(f"從檔案讀取資料時發生錯誤：{str(e)}")
            return None
    
    async def save_to_file(self, filepath: str, data: Any, *args, **kwargs) -> None:
        """儲存資料到本地檔案快取
        
        Args:
            filepath (str): 要儲存的JSON檔案路徑
            data (Any): 要儲存的資料（必須是可JSON序列化的資料）
            *args: 額外的位置參數
            **kwargs: 額外的關鍵字參數
        """
        try:
            # 確保目標目錄存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8-sig') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except (TypeError, PermissionError, OSError) as e:
            print(f"儲存資料到檔案時發生錯誤：{str(e)}")
            raise

    @abstractmethod
    async def fetch_from_source(self, *args, **kwargs) -> Any:
        """從最終來源取得資料（如網路、其他服務等）
        因為涉及網路io 因此要logger info"""
        pass



