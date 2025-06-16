from typing import Dict

from tnfsh_timetable_core.index.models import (
    IndexResult,
    ReverseIndexResult,
    ReverseMap,
)

class ReverseIndexBuilder:
    """負責建立索引的反向查詢表"""
    
    @staticmethod
    def build(index: IndexResult) -> ReverseIndexResult:
        """將正向索引轉換為反向查詢表
        
        Args:
            index: 原始索引資料
            
        Returns:
            ReverseIndexResult: 反向查詢表
        """
        result: ReverseIndexResult = {}
        
        # 處理教師資料
        ReverseIndexBuilder._add_to_reverse_index(index.teacher.data, result)
        # 處理班級資料
        ReverseIndexBuilder._add_to_reverse_index(index.class_.data, result)
        
        return result
    
    @staticmethod
    def _add_to_reverse_index(
        data: Dict[str, Dict[str, str]],
        result: ReverseIndexResult
    ) -> None:
        """將資料添加到反向索引中
        
        Args:
            data: 原始資料字典
            result: 要添加到的結果字典
        """
        for category, items in data.items():
            for name, url in items.items():
                result[name] = ReverseMap(url=url, category=category)
