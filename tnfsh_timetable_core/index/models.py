from typing import Optional, TypeAlias, Dict, Union
from pydantic import BaseModel, RootModel

def dict_like(cls):

    def _get_root(self):
        return self.root

    setattr(cls, '__getitem__', lambda self, k: _get_root(self)[k])
    setattr(cls, '__setitem__', lambda self, k, v: _get_root(self).__setitem__(k, v))
    setattr(cls, '__delitem__', lambda self, k: _get_root(self).__delitem__(k))
    setattr(cls, '__contains__', lambda self, k: k in _get_root(self))
    setattr(cls, '__iter__', lambda self: iter(_get_root(self)))
    setattr(cls, '__len__', lambda self: len(_get_root(self)))
    setattr(cls, 'get', lambda self, k, default=None: _get_root(self).get(k, default))
    setattr(cls, 'keys', lambda self: _get_root(self).keys())
    setattr(cls, 'values', lambda self: _get_root(self).values())
    setattr(cls, 'items', lambda self: _get_root(self).items())
    setattr(cls, 'update', lambda self, *args, **kwargs: _get_root(self).update(*args, **kwargs))
    return cls


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

    def __getitem__(self, key: str) -> URL:

        if key == "url":
            return self.url
        elif key == "category":
            return self.category

@dict_like
class ReverseIndexResult(RootModel[Dict[str, ReverseMap]]): 
    
    """
    表示反查表的主結構，將班級和老師的資料轉換為可快速查詢的格式。
    """
    
    pass

class AllTypeIndexResult(BaseModel):
    
    """
    表示所有類型的索引結果，包括班級和教師的資料。
    """
    
    index: IndexResult
    reverse_index: ReverseIndexResult


