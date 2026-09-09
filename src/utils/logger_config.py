import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(log_file="logs/app.log"):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    handler = RotatingFileHandler(
        filename=log_file, maxBytes=1024 * 1024, encoding="utf-8", backupCount=2
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
