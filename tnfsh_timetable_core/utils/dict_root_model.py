from __future__ import annotations
from typing import TypeVar, Generic, Dict, Any, Iterable, Tuple
from pydantic import RootModel

K = TypeVar("K")
V = TypeVar("V")

class DictRootModel(RootModel[Dict[K, V]], Generic[K, V]):

    def __getitem__(self, key: K) -> V:
        return self.root[key]

    def __setitem__(self, key: K, value: V) -> None:
        self.root[key] = value

    def __delitem__(self, key: K) -> None:
        del self.root[key]

    def __contains__(self, key: K) -> bool:
        return key in self.root

    def __len__(self) -> int:
        return len(self.root)

    def get(self, key: K, default: Any = None) -> V | None:
        return self.root.get(key, default)

    def keys(self):
        return self.root.keys()

    def values(self):
        return self.root.values()

    def items(self) -> Iterable[Tuple[K, V]]:
        return self.root.items()

    def update(self, *args: Any, **kwargs: Any) -> None:
        self.root.update(*args, **kwargs)

    def setdefault(self, key: K, default: V) -> V:
        return self.root.setdefault(key, default)

    def pop(self, key: K, default: Any = None) -> V:
        return self.root.pop(key, default)

