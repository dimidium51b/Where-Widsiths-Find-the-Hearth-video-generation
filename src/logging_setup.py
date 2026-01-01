import logging
import sys
from datetime import datetime
from pathlib import Path

# THis is a nice logging sceme I used in some other projects and adapted for rendering
# Why is this important???
# The rendering process tooks days! And shit happens, here as well.
# The renderer got started over night some times and got stuck. If this happens,
# at least having some logs helps to improve

# By the way, if someone know, why this takes so long, please let me know :-)


def setup_logging(log_dir: str = '.', level: int = logging.INFO) -> str:
    """Configure root logger to log to both console and a timestamped file.

    Returns the path to the created log file.
    """
    logger = logging.getLogger()
    # Prevent adding handlers multiple times
    if logger.handlers:
        return getattr(logger, "_log_file", "")

    logger.setLevel(level)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_path = Path(log_dir) / f"render_{ts}.log"

    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setLevel(logging.DEBUG)  # file is more verbose (includes DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # store created log path for idempotence
    setattr(logger, "_log_file", str(log_path))

    logger.info("================================================================================")
    logger.info("Starting 51 Pegasi B Renderer")
    logger.info("================================================================================")

    return str(log_path)
