import logging
import sys

from pythonjsonlogger import json as jsonlogger  # changed


def setup_logging():
    logger = logging.getLogger("enterprise_rag")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


logger = setup_logging()
