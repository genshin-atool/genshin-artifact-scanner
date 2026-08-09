import logging
import sys


def setup_logger():
    """配置全局唯一logger"""
    # 创建唯一命名的logger
    logger = logging.getLogger("genshin-calculation-logger")

    # 避免重复初始化
    if logger.handlers:
        return logger

    # 配置格式
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    # 关键配置
    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # 阻止传播到root logger

    return logger


Log = setup_logger()
