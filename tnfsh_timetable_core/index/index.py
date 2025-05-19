from datetime import datetime
from typing import Dict, Optional
from .models import IndexResult, ReverseIndex
from .crawler import request_index

class Index:
    """台南一中課表索引的單例類別"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls) -> 'Index':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        # 確保初始化只執行一次
        if not Index._initialized:
            self.base_url = "http://w3.tnfsh.tn.edu.tw/deanofstudies/course/"
            self.index = self._get_index()
            self.reverse_index = self._build_reverse_index()
            Index._initialized = True

    def _get_index(self) -> IndexResult:
        """取得完整的台南一中課表索引"""
        return request_index(self.base_url)
    
    def _build_reverse_index(self) -> ReverseIndex:
        """建立反查表，將老師/班級對應到其 URL 和分類。

        Returns:
            ReverseIndex: 反查表結構為 {老師/班級: {url: url, category: category}}
        """
        reverse_index = {}
        
        # 處理教師資料
        if "teacher" in self.index:
            teacher_data = self.index["teacher"]["data"]
            for subject, teachers in teacher_data.items():
                for teacher_name, teacher_url in teachers.items():
                    reverse_index[teacher_name] = {
                        "url": teacher_url,
                        "category": subject
                    }

        # 處理班級資料
        if "class" in self.index:
            class_data = self.index["class"]["data"]
            for grade, classes in class_data.items():
                for class_num, class_url in classes.items():
                    reverse_index[class_num] = {
                        "url": class_url,
                        "category": grade
                    }
        
        return reverse_index
    
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
            export_data["index"] = self.index
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
    
    def refresh(self) -> None:
        """重新載入索引資料"""
        self.index = self._get_index()
        self.reverse_index = self._build_reverse_index()
        
    @classmethod
    def fetch(cls) -> 'Index':
        """取得單例實例
        
        Returns:
            TNFSHClassTableIndex: 索引類別的單例實例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
