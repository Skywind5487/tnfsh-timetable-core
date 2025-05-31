from typing import Optional, TypeAlias, Dict, Union
import aiohttp
from aiohttp import client_exceptions
import asyncio
from bs4 import BeautifulSoup
import re
from tnfsh_timetable_core.index.models import IndexResult, ReverseIndexResult, GroupIndex, ReverseMap, AllTypeIndexResult

from tnfsh_timetable_core import TNFSHTimetableCore
core = TNFSHTimetableCore()
logger = core.get_logger()

class FetchError(Exception):
    """爬取課表時可能發生的錯誤"""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

async def request_html(base_url: str, url: str, timeout: int = 15, from_file_path: Optional[str] = None, max_retries: int = 3, retry_delay: float = 1.0) -> BeautifulSoup:
    """非同步取得網頁內容並解析
    
    Args:
        base_url (str): 基礎 URL
        url (str): 相對路徑 URL
        timeout (int): 請求超時時間
        from_file_path (Optional[str]): 可選的檔案路徑，若提供則從該檔案讀取
        max_retries (int, optional): 最大重試次數. 預設為 3
        retry_delay (float, optional): 重試間隔秒數. 預設為 1.0
        
    Returns:
        BeautifulSoup: 解析後的 BeautifulSoup 物件
        
    Raises:
        aiohttp.ClientError: 當網頁請求失敗時
        Exception: 當解析 HTML 失敗時
    """
    if from_file_path:
        logger.debug(f"📂 從檔案讀取：{from_file_path}")
        with open(from_file_path, 'r', encoding='utf-8') as f:
            return BeautifulSoup(f.read(), 'html.parser')
    
    full_url = base_url + url
    logger.debug(f"🌐 準備請求網址：{full_url}")
    
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for attempt in range(max_retries):
        try:
            logger.debug(f"📡 發送請求 (嘗試 {attempt + 1}/{max_retries})")
            async with aiohttp.ClientSession() as session:
                async with session.get(full_url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    response.raise_for_status()
                    content = await response.read()
                    logger.debug(f"📥 收到回應")
                    soup = BeautifulSoup(content, 'html.parser')
                    logger.debug(f"✅ HTML 解析完成")
                    return soup

        except client_exceptions.ClientResponseError as e:
            error_msg = f"HTTP 狀態碼錯誤 {e.status}: {e.message}"
            logger.warning(f"⚠️ {error_msg}")
            if attempt + 1 < max_retries:
                logger.info(f"🔄 等待 {retry_delay} 秒後重試...")
                await asyncio.sleep(retry_delay)
                continue
            raise aiohttp.ClientError(error_msg)

        except client_exceptions.ClientConnectorError as e:
            error_msg = f"連線錯誤：{str(e)}"
            logger.warning(f"⚠️ {error_msg}")
            if attempt + 1 < max_retries:
                logger.info(f"🔄 等待 {retry_delay} 秒後重試...")
                await asyncio.sleep(retry_delay)
                continue
            raise aiohttp.ClientError(error_msg)

        except (client_exceptions.ServerTimeoutError, asyncio.TimeoutError):
            error_msg = "請求超時"
            logger.warning(f"⚠️ {error_msg}")
            if attempt + 1 < max_retries:
                logger.info(f"🔄 等待 {retry_delay} 秒後重試...")
                await asyncio.sleep(retry_delay)
                continue
            raise aiohttp.ClientError(error_msg)

        except client_exceptions.ClientError as e:
            error_msg = f"網路請求錯誤：{str(e)}"
            logger.warning(f"⚠️ {error_msg}")
            if attempt + 1 < max_retries:
                logger.info(f"🔄 等待 {retry_delay} 秒後重試...")
                await asyncio.sleep(retry_delay)
                continue
            raise aiohttp.ClientError(error_msg)

        except Exception as e:
            error_msg = f"未預期的錯誤：{str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FetchError(error_msg)

def parse_html(soup: BeautifulSoup, url: str) -> GroupIndex:
    """解析網頁內容
    
    Args:
        soup (BeautifulSoup): 要解析的 BeautifulSoup 物件
        url (str): 該索引的 URL

    Returns:
        GroupIndex: 解析後的索引資料結構
    """
    parsed_data = {}
    current_category = None
    
    for tr in soup.find_all("tr"):
        category_tag = tr.find("span")
        if category_tag and not tr.find("a"):
            current_category = category_tag.text.strip()
            parsed_data[current_category] = {}
        for a in tr.find_all("a"):
            link = a.get("href")
            text = a.text.strip()
            if text.isdigit() and link:
                parsed_data[current_category][text] = link
            else:
                match = re.search(r'([\u4e00-\u9fa5]+)', text)
                if match:
                    text = match.group(1)
                    parsed_data[current_category][text] = link
                else:
                    text = text.replace("\r", "").replace("\n", "").replace(" ", "").strip()
                    if len(text) > 3:
                        text = text[3:].strip()
                        parsed_data[current_category][text] = link
    
    return GroupIndex(url=url, data=parsed_data)


def reverse_index(index: IndexResult) -> ReverseIndexResult:
    """將索引資料轉換為反查表格式
    
    將 IndexResult 中的班級和老師資料轉換為 ReverseIndexResult 格式，
    方便快速查找特定班級或老師的資訊。
    
    Args:
        index (IndexResult): 原始索引資料
        
    Returns:
        ReverseIndexResult: 反查表格式的資料
    """
    result: ReverseIndexResult = {}
    
    # 處理老師資料
    for category, teachers in index.teacher.data.items():
        for teacher_name, url in teachers.items():
            result[teacher_name] = ReverseMap(url=url, category=category)
    
    # 處理班級資料
    for category, classes in index.class_.data.items():
        for class_name, url in classes.items():
            result[class_name] = ReverseMap(url=url, category=category)
    
    return result

async def request_all_index(base_url: str) -> IndexResult:
    """非同步獲取完整的課表索引
    
    Args:
        base_url (str): 基礎 URL
        
    Returns:
        IndexResult: 完整的課表索引資料
    """
    # 並行獲取教師和班級索引
    tasks = [
        request_html(base_url, "_TeachIndex.html"),
        request_html(base_url, "_ClassIndex.html")
    ]
    teacher_soup, class_soup = await asyncio.gather(*tasks)
    
    # 解析資料
    teacher_result = parse_html(teacher_soup, "_TeachIndex.html")
    class_result = parse_html(class_soup, "_ClassIndex.html")
    
    # 建立完整索引
    return IndexResult(
        base_url=base_url,
        root="index.html",
        class_=class_result,
        teacher=teacher_result
    )

def merge_results(index: IndexResult, reverse_index: ReverseIndexResult) -> AllTypeIndexResult:
    """合併索引和反查表結果
    
    Args:
        index (IndexResult): 完整的課表索引資料
        reverse_index (ReverseIndexResult): 反查表資料
        
    Returns:
        AllTypeIndexResult: 合併後的結果
    """
    return AllTypeIndexResult(
        index=index,
        reverse_index=reverse_index
    )

async def fetch_all_index(base_url: str) -> AllTypeIndexResult:
    """獲取所有類型的索引資料
    
    Args:
        base_url (str): 基礎 URL
        
    Returns:
        AllTypeIndexResult: 所有類型的索引資料
    """
    index_result = await request_all_index(base_url)
    reverse_index_result = reverse_index(index_result)
    return merge_results(index_result, reverse_index_result)

if __name__ == "__main__":
    # For test cases, see: tests/test_index/test_crawler.py
    pass
