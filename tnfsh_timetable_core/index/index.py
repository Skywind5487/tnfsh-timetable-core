from datetime import datetime
from typing import Dict, Optional
from tnfsh_timetable_core.index.models import IndexResult, ReverseIndexResult, AllTypeIndexResult
from tnfsh_timetable_core.index.crawler import request_all_index
from tnfsh_timetable_core.index.cache import fetch_with_cache
import json

class Index:
    """台南一中課表索引的單例類別"""
    
    base_url = "http://w3.tnfsh.tn.edu.tw/deanofstudies/course/"
    index: Optional[IndexResult] = None
    reverse_index: Optional[ReverseIndexResult] = None

    def __init__(self) -> None:
        pass

    async def fetch(self, refresh: bool = False) -> None:
        """初始化索引資料
        
        Args:
            refresh (bool): 是否強制重新從網路獲取資料
        """
        result: AllTypeIndexResult = await fetch_with_cache(self.base_url, refresh=refresh)
        if self.index is None or refresh:
            self.index = result.index
        if self.reverse_index is None or refresh:
            self.reverse_index = result.reverse_index
        #print(self.index.model_dump_json(indent=4))
        #print(json.dumps(self.reverse_index.model_dump(), indent=4, ensure_ascii=False))

    def export_json(self, export_type: str = "all", filepath: Optional[str] = None) -> str:
        """匯出索引資料為 JSON 格式
        
        Args:
            export_type (str): 要匯出的資料類型 ("index"/"reverse_index"/"all"，預設為 "all")
            filepath (str, optional): 輸出檔案路徑，若未指定則自動生成
            
        Returns:
            str: 實際儲存的檔案路徑
            
        Raises:
            ValueError: 當 export_type 不合法時
            Exception: 當檔案寫入失敗時
        """
        # 驗證 export_type
        valid_types = ["index", "reverse_index", "all"]

        if export_type.lower() not in valid_types:
            raise ValueError(f"不支援的匯出類型。請使用 {', '.join(valid_types)}")
        
        if export_type == "all":
            export_type = "index_all"
            
        # 準備要匯出的資料
        export_data = {}
        if export_type.lower() == "index":
            export_data["index"] = self.index.model_dump()
        elif export_type.lower() == "reverse_index":
            export_data["reverse_index"] = self.reverse_index
        else:  # all
            export_data = {
                "index": self.index,
                "reverse_index": self.reverse_index
            }

        # 加入匯出時間
        export_data["export_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 如果未指定檔案路徑，則自動生成
        if filepath is None:
            filepath = f"tnfsh_class_table_{export_type}.json"

        # 寫入 JSON 檔案
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            return filepath
        except Exception as e:
            raise Exception(f"Failed to write JSON file: {str(e)}")

if __name__ == "__main__":
    # For test cases, see: tests/test_index/test_index.py
    pass