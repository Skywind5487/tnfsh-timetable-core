from ast import Str
from calendar import c
from functools import cache, cached_property
from typing import Optional, TypeAlias, Dict, Union, List, Tuple, Literal
from datetime import datetime
import typing_extensions
from unittest.mock import Base
from pydantic import BaseModel, RootModel, Field, computed_field
from tnfsh_timetable_core.utils.dict_like import dict_like
from tnfsh_timetable_core.utils.dict_root_model import DictRootModel
import re

# ========================
# 🏷️ 基礎型別定義
# ========================


ItemMap: TypeAlias = Dict[str, str]  # e.g. {"黃大倬": "TA01.html"} 或 {"101": "C101101.html"}
CategoryMap: TypeAlias = Dict[str, ItemMap]  # e.g. {"國文科": {...}}, {"高一": {...}}

# ========================
# 📦 基礎資料結構
# ========================

class ReverseMap(BaseModel):
    """反向查詢的基本單位
    
    將老師/班級對應到其 URL 和分類，例如：
    {
        "url": "TA01.html",
        "category": "國文科"
    }
    或
    {
        "url": "C101101.html",
        "category": "高一"
    }
    """
    url: str
    category: str

    def __getitem__(self, key: str) -> str:
        if key == "url":
            return self.url
        elif key == "category":
            return self.category

class GroupIndex(BaseModel):
    """群組索引（如某科教師群或某年級班級群）
    
    包含：
    - url: 群組的基礎URL
    - data: 群組內的項目對照表
    """
    url: str
    data: CategoryMap

    def __getitem__(self, key: str) -> ItemMap:
        return self.data[key]

# 新定義
class TargetInfo(BaseModel):
    """每一個 ID 對應的實體資訊"""
    target: str  # 如 黃大倬、307
    category: str  # 如 國文科、高一
    url: str  # 如 TA01.html 或 C101101.html
    
    @computed_field
    @cached_property
    def role(self) -> Literal["teacher", "class"]:
        """根據 URL 的前綴判斷角色"""
        if self.url[0] == 'T':
            return "teacher"
        else:
            return "class"
        
    @computed_field
    @cached_property
    def id(self) -> str:
        """從 URL 中提取 ID"""
        return (self
                .url[1:]
                .removesuffix(".html")
                .removesuffix(".HTML")
        )  # 提取ID部分，不包含Role，去除前的 'T' 或 'C' 前綴和後綴的 .html

    @computed_field
    @cached_property
    def id_prefix(self) -> str:
        """提取 ID 的前綴部分"""
        if self.role == "teacher":
            match = re.match(r"^([A-Za-z]+)", self.id)
            return match.group(1) if match else ""
        else:
            return ""  # 班級沒有前綴部分
    
    @computed_field
    @cached_property
    def id_suffix(self) -> str | None:
        """提取 ID 的後綴部分"""
        if self.role == "teacher":
            match = re.match(r"^[A-Za-z]+(\d+)$", self.id)
            return match.group(1) if match else None
        else:
            return self.id.removesuffix(self.target)  # 班級ID不含前綴
        
# ========================
class NewCategoryMap(DictRootModel[str, TargetInfo]):
    """新的分類對照表結構"""
    pass

class NewGroupIndex(BaseModel):
    """新的群組索引結構"""
    url: str
    data: NewCategoryMap

# ========================
# 🔍 進階索引結構
# ========================

class IndexResult(BaseModel):
    """正向索引主結構
    
    包含：
    - base_url: 基礎URL
    - root: 根目錄
    - class_: 班級索引
    - teacher: 教師索引
    """
    base_url: str
    root: str
    class_: GroupIndex
    teacher: GroupIndex

class ReverseIndexResult(DictRootModel[str, ReverseMap]): 
    """反向索引主結構
    
    提供快速查詢功能的字典型結構，
    將目標名稱對應到其詳細資訊
    """
    pass


# 新定義
class DetailedIndex(BaseModel):
    """解析後的索引結構"""
    base_url: str
    root: str
    class_: NewGroupIndex
    teacher: NewGroupIndex

class AllTypeIndexResult(BaseModel):
    """完整索引結構
    
    整合了：
    - 正向索引
    - 反向索引
    - ID對照表
    """
    # Deprecated: 使用 detailed_index 和 Index.py 中的 Index[key] 替代 index 和 reverse_index
    index: IndexResult
    reverse_index: ReverseIndexResult
    
    # 新定義
    detailed_index: DetailedIndex
    id_to_info: Dict[str, TargetInfo]
    name_to_unique_info: Dict[str, TargetInfo]
    name_to_conflicting_ids: Dict[str, List[str]]


# ========================
# 💾 快取結構
# ========================

class CacheMetadata(BaseModel):
    """快取元數據"""
    cache_fetch_at: datetime = Field(description="資料從遠端抓取的時間")

class CachedIndex(BaseModel):
    """正向索引快取"""
    metadata: CacheMetadata
    data: IndexResult

class CachedReverseIndex(BaseModel):
    """反向索引快取"""
    metadata: CacheMetadata
    data: ReverseIndexResult

class CachedFullIndex(BaseModel):
    """完整索引快取"""
    metadata: CacheMetadata
    data: AllTypeIndexResult


