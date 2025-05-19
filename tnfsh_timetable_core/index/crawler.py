from typing import Optional, TypeAlias, Dict, Union
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
from pydantic import BaseModel

URL: TypeAlias = str
ItemMap: TypeAlias = Dict[str, URL]  # e.g. {"黃大倬": "TA01.html"} 或 {"101": "C101101.html"}
CategoryName: TypeAlias = str
CategoryMap: TypeAlias = Dict[CategoryName, ItemMap]  # e.g. {"國文科": {...}}, {"高一": {...}}

# ========================
# 📦 資料結構模型
# ========================

class GroupIndex(BaseModel):
    """
    表示一個類別的索引資料，例如班級、老師等。
    包含一個 URL 與一層巢狀字典結構的資料。
    """
    url: URL
    data: CategoryMap

    def __getitem__(self, key: str) -> ItemMap:
        return self.data[key]


class IndexResult(BaseModel):
    """
    表示 index 區塊的主結構，含有 base_url、root，以及班級與老師的索引資料。
    """
    base_url: URL
    root: str
    class_: GroupIndex
    teacher: GroupIndex

async def fetch_html(base_url: str, url: str, timeout: int = 10, from_file_path: Optional[str] = None) -> BeautifulSoup:
    """非同步取得網頁內容並解析
    
    Args:
        base_url (str): 基礎 URL
        url (str): 相對路徑 URL
        timeout (int): 請求超時時間
        from_file_path (Optional[str]): 可選的檔案路徑，若提供則從該檔案讀取
        
    Returns:
        BeautifulSoup: 解析後的 BeautifulSoup 物件
        
    Raises:
        aiohttp.ClientError: 當網頁請求失敗時
        Exception: 當解析 HTML 失敗時
    """
    if from_file_path:
        with open(from_file_path, 'r', encoding='utf-8') as f:
            return BeautifulSoup(f.read(), 'html.parser')
            
    async with aiohttp.ClientSession() as session:
        async with session.get(base_url + url, timeout=timeout) as response:
            response.raise_for_status()
            content = await response.read()
            return BeautifulSoup(content, 'html.parser')

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

async def fetch_index(base_url: str) -> IndexResult:
    """非同步獲取完整的課表索引
    
    Args:
        base_url (str): 基礎 URL
        
    Returns:
        IndexResult: 完整的課表索引資料
    """
    # 並行獲取教師和班級索引
    tasks = [
        fetch_html(base_url, "_TeachIndex.html"),
        fetch_html(base_url, "_ClassIndex.html")
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

# 更新主程式為非同步版本
if __name__ == "__main__":
    # http://w3.tnfsh.tn.edu.tw/deanofstudies/course/_TeachIndex.html
    base_url = "http://w3.tnfsh.tn.edu.tw/deanofstudies/course/"
    
    async def main():
        index_result = await fetch_index(base_url)
        with open("index.json", "w", encoding="utf-8") as f:
            f.write(index_result.model_dump_json(indent=4))
    
    # 在 Windows 上運行非同步程式
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
