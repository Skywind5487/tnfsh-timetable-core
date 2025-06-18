from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseCrawlerABC(ABC):
    """
    Crawler 層的抽象基底類，規範所有爬蟲/資料抓取器的標準介面。
    使用tenacity進行重試
    """
    def get_headers(self) -> Dict[str, str]:
        """
        獲取默認的 HTTP 請求頭
        
        Returns:
            Dict[str, str]: HTTP 請求頭字典
        """
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    @abstractmethod
    async def fetch_raw(self, *args, **kwargs) -> Any:
        """
        不做 url 的處理，直接請求以獲取原始數據，回傳BeautifulSoup物件
        
        Returns:
            Any: 原始數據（通常是 HTML 或 JSON）
        """
        pass

    @abstractmethod
    def parse(self, raw: Any, *args, **kwargs) -> Any:
        """
        處理BeautifulSoup並解析為結構化數據
        
        Args:
            raw: 原始數據
            
        Returns:
            Any: 解析後的數據
        """
        pass
    
    @abstractmethod
    async def fetch(self, *args, **kwargs) -> Any:
        """
        完整的抓取流程，通常是 fetch_raw 後進行 parse
        因為一定會有網路請求，所以不用加refresh
        
        Returns:
            Any: 解析後的數據
        """
        pass