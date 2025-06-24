from enum import IntEnum, auto
from tnfsh_timetable_core import TNFSHTimetableCore
core = TNFSHTimetableCore()
logger = core.get_logger(logger_level="DEBUG")

class RefreshLayer(IntEnum):
    """刷新層級枚舉，定義了不同的刷新層級"""
    INDEX      = auto()
    TIMETABLE  = auto()
    SLOT       = auto()
    ALGO       = auto()

DEPENDENCY = {
    RefreshLayer.INDEX:     (),
    RefreshLayer.TIMETABLE: (RefreshLayer.INDEX,),
    RefreshLayer.SLOT:      (RefreshLayer.TIMETABLE,),
    RefreshLayer.ALGO:      (RefreshLayer.SLOT,),
}

def expand_refresh(refresh_layers: set[RefreshLayer]) -> set[RefreshLayer]:
    """閉包展開：補齊所有上游依賴"""
    need = set(refresh_layers)
    queue = list(refresh_layers)
    while queue:
        node = queue.pop()
        for parent in DEPENDENCY[node]:
            if parent not in need:
                need.add(parent)
                queue.append(parent)
    logger.debug(f"🔄 展開刷新層級：{need}")
    return need


if __name__ == "__main__":
    # 測試展開函數
    test_layers = {RefreshLayer.TIMETABLE}
    expanded = expand_refresh(test_layers)
    print(f"原始層級: {test_layers}, 展開後層級: {expanded}")
    # 預期輸出: 原始層級: {TIMETABLE, SLOT}, 展開後層級: {INDEX, TIMETABLE, SLOT}