# logger.py
import logging
import os
import inspect
from dotenv import load_dotenv

load_dotenv()
default_log_level = "INFO"  # 預設日誌等級
valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

# 取得並驗證環境變數中的日誌等級
env_level = os.getenv("LOG_LEVEL", default_log_level).upper()
LOG_LEVEL = env_level if env_level in valid_levels else default_log_level

handler = logging.StreamHandler()
handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))


def get_logger(logger_level: str = None) -> logging.Logger:
    """獲取 logger 實例
    
    Args:
        logger_level (str, optional): 日誌等級，如果未指定則使用全域設定的 LOG_LEVEL。
            可用等級：DEBUG、INFO、WARNING、ERROR、CRITICAL

    Returns:
        logging.Logger: 配置好的 logger 實例
    """
    # 自動取得呼叫此函數的模組名稱
    caller_frame = inspect.stack()[1]
    module = inspect.getmodule(caller_frame[0])
    name = module.__name__ if module else "unknown"

    logger = logging.getLogger(name)
    
    # 如果沒有指定等級，使用全域設定
    level = (logger_level or LOG_LEVEL).upper()
    
    # 確保日誌等級有效
    if level not in valid_levels:
        level = LOG_LEVEL
        
    logger.setLevel(getattr(logging, level))

    # 避免重複加 handler
    if not logger.hasHandlers():
        formatter = logging.Formatter(f"[%(levelname)s] [{name}] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

def set_log_level(level: str):
    """設定全域日誌等級

    Args:
        level (str): 日誌等級，例如 "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
            如果提供了無效的等級，將使用預設等級 (INFO)
    """
    global LOG_LEVEL
    level = level.upper()
    if level not in valid_levels:
        level = default_log_level
    
    LOG_LEVEL = level
    handler.setLevel(getattr(logging, LOG_LEVEL))
    logging.getLogger().setLevel(getattr(logging, LOG_LEVEL))