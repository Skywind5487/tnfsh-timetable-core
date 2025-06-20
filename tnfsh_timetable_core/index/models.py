"""臺南一中課表系統的資料結構定義

此模組定義了課表系統中使用的所有資料結構，包含：
1. 索引結構（教師、班級、課程等）
2. 分類映射（科目、年級等）
3. 快取機制
4. 資料轉換工具

主要的資料流向：
raw HTML -> 基礎結構 -> 進階索引 -> 快取結構
"""

from functools import cached_property
from typing import Optional, TypeAlias, Dict, List, Literal
from datetime import date, datetime
import re
from pydantic import BaseModel, RootModel, Field, computed_field
from tnfsh_timetable_core.utils.dict_root_model import DictRootModel

# ========================
# 🏷️ 舊版基礎型別（向下相容）
# ========================

ItemMap: TypeAlias = Dict[str, str]  # 名稱到URL的映射，如 {"黃大倬": "TA01.html"}
CategoryMap: TypeAlias = Dict[str, ItemMap]  # 分類到項目的映射，如 {"國文科": {"黃大倬": "TA01.html"}}

# ========================
# 📦 基礎資料結構（向下相容）
# ========================

class ReverseMap(BaseModel):
    """反向查詢的基本單位（舊版）
    
    用於快速查找目標的所屬分類和URL：
    
    教師範例：
    {
        "黃大倬": {
            "url": "TA01.html",
            "category": "國文科"
        }
    }
    
    班級範例：
    {
        "307": {
            "url": "C101307.html",
            "category": "高三"
        }
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


# ========================
# 🎯 核心資料結構（新版）
# ========================

class TargetInfo(BaseModel):
    """目標實體的完整資訊
    
    這是系統中最基本的資料單位，記錄了一個目標（教師或班級）的所有必要資訊。
    
    欄位：
    - target: 顯示名稱，如 "黃大倬" 或 "307"
    - category: 所屬分類，如 "國文科" 或 "高三"
    - url: 課表連結，如 "TA01.html" 或 "C101307.html"
    
    衍生欄位（自動計算）：
    - role: 角色類型 ("teacher" 或 "class")
    - id: 純ID，如 "A01" 或 "101307"
    - id_prefix: ID前綴，如 "A" 或 ""
    - id_suffix: ID後綴，如 "01" 或 "307"
    """
    target: str
    category: str
    url: str
    
    
        
    @computed_field
    @cached_property
    def id(self) -> str:
        """從 URL 中提取 ID"""
        return (self
                .url
                .removesuffix(".html")
                .removesuffix(".HTML")
        )  # 提取ID部分，不包含Role，去除前的 'T' 或 'C' 前綴和後綴的 .html
    
    @computed_field
    @cached_property
    def role(self) -> Literal["teacher", "class"]:
        """根據 URL 的前綴判斷角色"""
        if self.id[0] == 'T':
            return "teacher"
        else:
            return "class"
        
    @computed_field
    @cached_property
    def id_prefix(self) -> str:
        """提取 ID 的前綴部分"""
        if self.role == "teacher":
            match = re.match(r"^([A-Za-z]+)", self.id[1:])
            return match.group(1) if match else ""
        else:
            return self.id.removesuffix(self.target)   # 班級的前綴就是ID本身去掉target

    @computed_field
    @cached_property
    def id_suffix(self) -> str | None:
        """提取 ID 的後綴部分"""
        if self.role == "teacher":
            match = re.match(r"^[A-Za-z]+(\d+)$", self.id[1:])
            return match.group(1) if match else None
        else:
            return self.target  # 班級的後綴就是目標名稱，沒有額外的後綴部分


def get_id_from_parts(role:Literal["teacher", "class"], id_prefix: str, id_suffix: str | None, target: str | None) -> str:
    """根據前綴和後綴組合出完整的 ID"""
    if role == "teacher":
        if id_suffix is not None:
            return f"{id_prefix}{id_suffix}"
        else:
            raise ValueError("教師的 ID 後綴不能為 None")
    else:
        if target is not None:
            # 班級的 ID 是由前綴和目標組成
            return f"{id_prefix}{target}"
        else:
            raise ValueError("班級的target不能為 None")

def get_url_from_parts(role:Literal["teacher", "class"], id_prefix: str, id_suffix: str | None, target: str) -> str:
    """
    根據前綴和後綴組合出完整的 URL
    可能有.html 或 .HTML 後綴
    但都可以用
    """
    if role == "teacher":
        return f"T{get_id_from_parts(role, id_prefix, id_suffix, target)}.html"
    else:
        return f"C{get_id_from_parts(role, id_prefix, id_suffix, target)}.html"

# ========================
# 🗂️ 索引結構（新版）
# ========================

class NewItemMap(DictRootModel[str, TargetInfo]):
    """單一分類下的項目映射表
    
    將 ID 映射到對應的 TargetInfo
    例如：{
        "A01": TargetInfo(target="黃大倬"...),
        "A02": TargetInfo(target="王小明"...)
    }
    """
    pass

class NewCategoryMap(DictRootModel[str, NewItemMap]):
    """分類索引結構
    
    提供兩層快速查找：
    1. 通過分類查找（如 "國文科"）
    2. 通過 ID 查找（如 "A01"）
    
    結構範例：
    {
        "國文科": {  # 第一層：分類名稱
            "A01": TargetInfo(...),  # 第二層：ID -> 資訊
            "A02": TargetInfo(...)
        },
        "數學科": {
            "B01": TargetInfo(...),
            "B02": TargetInfo(...)
        }
    }
    """
    pass

class NewGroupIndex(BaseModel):
    """群組索引（教師群或班級群）
    
    以分類為基礎的索引結構，用於組織和快速查找目標。
    
    欄位：
    - url: 群組的基礎URL（如 _TeachIndex.html）
    - last_update: 最後更新時間
    - data: 分類索引結構，詳見 NewCategoryMap
    """
    url: str
    last_update: str
    data: NewCategoryMap

    @property
    def last_update_datetime(self) -> datetime:
        """將 last_update 字符串轉換為 datetime 對象"""
        return datetime.strptime(self.last_update, "%Y/%m/%d %H:%M:%S")

# ========================
# 🔍 組合索引結構
# ========================

class IndexResult(BaseModel):
    """基礎索引（舊版，用於向下相容）
    
    提供簡單的分類式查找功能：
    base_url/root -> class_/teacher -> category -> target
    
    欄位：
    - base_url: 基礎URL，如 http://w3.tnfsh.tn.edu.tw/deanofstudies/course
    - root: 入口頁面，如 index.html
    - class_: 班級群組索引
    - teacher: 教師群組索引
    """
    base_url: str
    root: str
    class_: GroupIndex
    teacher: GroupIndex

class ReverseIndexResult(DictRootModel[str, ReverseMap]): 
    """反向索引（舊版，用於向下相容）
    
    通過名稱直接查找資訊：
    target_name -> { url, category }
    """
    pass

class DetailedIndex(BaseModel):
    """新版進階索引結構
    
    提供多層次、結構化的查找功能：
    1. 通過分類（category）
    2. 通過 ID（target_id）
    
    欄位：
    - base_url: 系統基礎URL
    - root: 系統入口頁面
    - class_: 班級進階索引
    - teacher: 教師進階索引
    """
    base_url: str
    root: str
    last_update: str  # 最後更新時間
    class_: NewGroupIndex
    teacher: NewGroupIndex

    @property
    def last_update_datetime(self) -> datetime:
        """將 last_update 字符串轉換為 datetime 對象"""
        return datetime.strptime(self.last_update, "%Y/%m/%d %H:%M:%S")

class FullIndexResult(BaseModel):
    """完整索引系統
    
    整合所有索引功能，提供多種查找途徑：
    1. 舊版相容：通過 index 和 reverse_index（已棄用）
    2. 結構化查找：通過 detailed_index
    3. 直接查找：通過 id_to_info 和 target_to_unique_info
    4. 衝突處理：通過 target_to_conflicting_ids
    
    資料查找順序：
    1. 先用 target_to_unique_info 嘗試直接查找
    2. 如果名稱在 target_to_conflicting_ids 中，表示有重複
    3. 需要通過 id_to_info 取得特定目標
    4. 可用 detailed_index 瀏覽分類結構
    """
    # 舊版相容層（已棄用）
    index: IndexResult | None = None
    reverse_index: ReverseIndexResult | None = None

    # 新版核心功能
    detailed_index: DetailedIndex
    id_to_info: Dict[str, TargetInfo]  # ID -> 目標資訊的全域映射
    target_to_unique_info: Dict[str, TargetInfo]  # 唯一名稱 -> 目標資訊
    target_to_conflicting_ids: Dict[str, List[str]]  # 重複名稱 -> ID列表


# ========================
# 💾 快取系統
# ========================

class CacheMetadata(BaseModel):
    """快取元數據
    
    記錄快取的基本資訊，用於判斷快取是否需要更新
    """
    cache_fetch_at: datetime = Field(description="資料從遠端抓取的時間")

class CachedIndex(BaseModel):
    """舊版索引快取結構
    
    用於儲存基礎索引資訊（向下相容）
    """
    metadata: CacheMetadata
    data: IndexResult

class CachedReverseIndex(BaseModel):
    """舊版反向索引快取結構
    
    用於儲存反向查找資訊（向下相容）
    """
    metadata: CacheMetadata
    data: ReverseIndexResult

class CachedFullIndex(BaseModel):
    """完整快取系統
    
    提供三層快取機制：
    1. 記憶體快取（最快）
    2. 檔案快取（中等）
    3. 網路來源（最慢）
    
    快取更新策略：
    1. 優先使用記憶體快取
    2. 記憶體無效時使用檔案快取
    3. 檔案過期時從網路更新
    """
    metadata: CacheMetadata
    data: FullIndexResult

