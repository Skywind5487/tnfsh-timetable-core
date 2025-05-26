# logger.py
import logging
import os
import inspect
from dotenv import load_dotenv

load_dotenv()
default_log_level = "INFO"
LOG_LEVEL = os.getenv("LOG_LEVEL", default_log_level).upper()

class SilentHandler(logging.Handler):
    def emit(self, record):
        pass

def get_logger(logger_level: str = "DEBUG") -> logging.Logger:
    caller_frame = inspect.stack()[1]
    module = inspect.getmodule(caller_frame[0])
    name = module.__name__ if module else "unknown"

    logger = logging.getLogger(name)

    # 避免重複加 handler
    if not logger.hasHandlers():
        if LOG_LEVEL == "NONE":
            logger.addHandler(SilentHandler())
            logger.setLevel(logging.CRITICAL + 10)  # 什麼都不顯示
        else:
            handler = logging.StreamHandler()
            handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
            formatter = logging.Formatter(f"[%(levelname)s] [{name}] %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(getattr(logging, logger_level, logging.INFO))

    return logger
