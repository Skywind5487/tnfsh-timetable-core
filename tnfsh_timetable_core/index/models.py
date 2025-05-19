from typing import Optional, TypeAlias, Dict, Union
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

class ReverseMap(BaseModel):
    """
    表示反查表的結構，將老師/班級對應到其 URL 和分類。
    example:
        {
            "url": "TA01.html",
            "category": "國文科"
        }
        or
        {
            "url": "C101101.html",
            "category": "高一"
        }
    """
    url: URL
    category: CategoryName

ReverseIndexResultDict: TypeAlias = Dict[str, ReverseMap]  # e.g. {"黃大倬": {...}} or {"101": {...}}

class AllTypeIndexResult(BaseModel):
    """
    表示所有類型的索引結果，包括班級和教師的資料。
    """
    index: IndexResult
    reverse_index: ReverseIndexResultDict