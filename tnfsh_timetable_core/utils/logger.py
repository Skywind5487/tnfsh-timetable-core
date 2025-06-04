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


def _get_caller_module_name(default_name: str = "unknown") -> str:
    """
    嘗試從呼叫者的 frame 取得 __name__，若取不到就回傳 default_name
    """
    try:
        frame_info = inspect.stack()[1]
        frame = frame_info.frame
        module_name = frame.f_globals.get("__name__", None)
        if isinstance(module_name, str) and module_name:
            return module_name
        else:
            return default_name
    except Exception:
        return default_name


def get_logger(logger_level: str = None, default_module: str = "core_default") -> logging.Logger:
    """
    獲取 logger 實例

    Args:
        logger_level (str, optional): 日誌等級，如果未指定則使用全域設定的 LOG_LEVEL。
        default_module (str, optional): 如果無法從呼叫者 frame 取得模組名稱，則使用此預設名稱。

    Returns:
        logging.Logger: 配置好的 logger 實例
    """
    name = _get_caller_module_name(default_name=default_module)

    logger = logging.getLogger(name)

    level = (logger_level or LOG_LEVEL).upper()
    if level not in valid_levels:
        level = LOG_LEVEL

    logger.setLevel(getattr(logging, level))

    if not logger.hasHandlers():
        formatter = logging.Formatter(f"[%(levelname)s] [{name}] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

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
    handler.setLevel(getattr(logging, LOG_LEVEL))
    logging.getLogger().setLevel(getattr(logging, LOG_LEVEL))
