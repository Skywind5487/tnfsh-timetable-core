from __future__ import annotations
from typing import TypeVar, Generic, Dict, Any
from pydantic import RootModel
from collections.abc import MutableMapping


K = TypeVar("K")
V = TypeVar("V")

class DictRootModel(RootModel[Dict[K, V]], MutableMapping[K, V], Generic[K, V]):
    """
    📦 DictRootModel：結合 Pydantic 的 RootModel 與 dict-like 行為的泛型模型。

    ✅ 繼承結構說明（依 MRO 順序）：
    - RootModel[Dict[K, V]] → 繼承自 BaseModel
        提供整體以 dict 為 root 的 Pydantic 驗證、序列化與型別支援。
        可直接接收一個字典作為資料模型的根、或以(key=value, ...)的形式傳入。
    - MutableMapping[K, V] → 繼承自 Mapping
        提供 dict-like 的可變操作行為。

    === 🔧 來自 RootModel 的功能（Pydantic 2） ===
    - root 屬性即為整體資料（Dict[K, V]）
    - model_validate(), model_dump(): 支援資料驗證與序列化
    - copy(), deepcopy(), __eq__()(主要會採用的__eq__方法，並非Mapping的), __str__(), __repr__() 等常見方法

    === 🧱 來自 BaseModel（RootModel 的父類） ===
    - 支援資料模型的表示、複製、比較與輸出
    - 預設的 __iter__ 會遍歷 root（非預期 dict 行為），需覆寫以改為 dict key 迭代

    === 🔁 來自 MutableMapping 的 dict 行為（mutable，可變）===
    ✅ 本類別已手動實作的 5 個必要方法：
    - __getitem__(key)
    - __setitem__(key, value)
    - __delitem__(key)
    - __iter__()
    - __len__()

    🧩 MutableMapping 自動提供的行為（無需手動實作）：
    - pop(), popitem(), setdefault(), update(), clear()
    - 需要: __setitem__(), __delitem__()

    === 🧩 來自 Mapping 的唯讀介面（dict-like readonly）===
    - get(), __contains__(), keys(), items(), values(), __eq__()(會優先使用 RootModel 的 __eq__ 方法)
    - 需要: __getitem__(), __iter__(), __len__()

    📌 使用效果：
    - 能像 dict 一樣進行讀取、寫入、刪除、遍歷與方法操作
    - 同時具備 Pydantic 的資料驗證、轉換與型別安全性
    - 適合以 dict 為主體的資料模型場景
    """

    def __getitem__(self, key: K) -> V:
        return self.root[key]

    def __setitem__(self, key: K, value: V) -> None:
        self.root[key] = value

    def __delitem__(self, key: K) -> None:
        del self.root[key]

    def __contains__(self, key: object) -> bool:
        return key in self.root

    def __iter__(self) -> Any:  # Iterator[K]:
        return iter(self.root)
    
    def __len__(self) -> int:
        return len(self.root)
