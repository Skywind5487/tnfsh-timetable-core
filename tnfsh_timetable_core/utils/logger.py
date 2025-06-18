# logger.py
import logging
import os
from pathlib import Path
from typing import Any, Optional
from functools import partialmethod
from dotenv import load_dotenv

# 定義新的日誌等級 DETAIL（比 DEBUG 更詳細）
DETAIL_LEVEL = 5  # DEBUG 是 10，所以這個要更低
logging.addLevelName(DETAIL_LEVEL, 'DETAIL')

# 擴展 Logger 類別
class DetailLogger(logging.Logger):
    """
    擴展的 Logger 類別，添加 DETAIL 等級
    """
    def detail(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """
        以 DETAIL 等級記錄日誌消息

        Args:
            msg: 要記錄的消息
            *args: 格式化參數
            **kwargs: 關鍵字參數
        """
        if self.isEnabledFor(DETAIL_LEVEL):
            self._log(DETAIL_LEVEL, msg, args, **kwargs)

# 註冊擴展的 Logger 類別
logging.setLoggerClass(DetailLogger)

# 嘗試從不同位置加載 .env 文件
possible_env_paths = [
    Path.cwd() / '.env',  # 當前工作目錄
    Path(__file__).parent.parent.parent / '.env',  # 專案根目錄
]

for env_path in possible_env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

default_log_level = "INFO"
valid_levels = ['DETAIL', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

# 取得並驗證環境變數中的日誌等級
env_level = os.getenv("LOG_LEVEL", default_log_level).upper()
LOG_LEVEL = env_level if env_level in valid_levels else default_log_level

# 創建全局的 handler
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, LOG_LEVEL))

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG:    "\033[34m",  # 藍
        logging.INFO:     "\033[32m",  # 綠
        logging.WARNING:  "\033[33m",  # 黃
        logging.ERROR:    "\033[31m",  # 紅
        logging.CRITICAL: "\033[41m\033[97m",  # 白字紅底
    }
    RESET = "\033[0m"

    def format(self, record):
        # 獲取完整路徑
        pathname = Path(record.pathname)
        # 只取最後兩層：父資料夾/檔案名
        relative_path = f"{pathname.parent.name}/{pathname.name}"
        
        color = self.COLORS.get(record.levelno, self.RESET)
        prefix = f"{color}[{relative_path}:{record.lineno}] {self.RESET}"
        return f"{prefix} {record.getMessage()}"

formatter = ColorFormatter('%(message)s')
console_handler.setFormatter(formatter)


def get_logger(name: str = None, logger_level : str = None) -> logging.Logger:
    """
    獲取 logger 實例

    Args:
        name (str, optional): logger 名稱。如果未指定，將使用調用模組的 __name__
        level (str, optional): 日誌等級，如果未指定則使用全域設定的 LOG_LEVEL

    Returns:
        logging.Logger: 配置好的 logger 實例
    """
    # 如果沒有提供名稱，使用調用模組的 __name__
    if name is None:
        import inspect
        frame = inspect.currentframe()
        try:
            # 獲取調用者的幀
            caller_frame = frame.f_back
            if caller_frame is not None:
                name = caller_frame.f_globals.get('__name__', 'unknown')
            else:
                name = 'unknown'
        finally:
            del frame  # 清理引用，避免循環引用

    logger = logging.getLogger(name)
    
    # 設置日誌等級
    log_level = (logger_level or LOG_LEVEL).upper()
    if log_level not in valid_levels:
        log_level = LOG_LEVEL
    logger.setLevel(getattr(logging, log_level))

    # 如果 logger 還沒有處理器，添加控制台處理器
    if not logger.handlers:
        logger.addHandler(console_handler)

    # 禁用向上傳播，避免重複日誌
    logger.propagate = False

    return logger


def set_log_level(level: str):
    """
    設定全域日誌等級

    Args:
        level (str): 日誌等級，例如 "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    """
    global LOG_LEVEL
    level = level.upper()
    if level not in valid_levels:
        level = default_log_level

    LOG_LEVEL = level
    console_handler.setLevel(getattr(logging, LOG_LEVEL))

    # 更新所有現有的 logger
    for logger_name in logging.root.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, LOG_LEVEL))
