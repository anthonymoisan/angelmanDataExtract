# logger.py
import logging
import sys

def setup_logger(log_file="exportBI.log", debug=False):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    formatter = logging.Formatter('%(asctime)s| %(levelname)-7s| %(message)s')

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG if debug else logging.INFO)
    ch.setFormatter(formatter)

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    logger.handlers = []  # Avoid duplicate logs
    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger