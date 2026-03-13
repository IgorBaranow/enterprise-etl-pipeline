import logging
import sys
from pathlib import Path

# Resolve the absolute path to the root 'logs' directory, keeping it relative to this file's location
BASE_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

def get_logger(script_name: str, region_code: str = "Global") -> logging.Logger:
    """
    Configures and returns a custom logger with a dual-handler setup.
    - Writes detailed DEBUG logs to a specific text file (for developer troubleshooting).
    - Streams clean INFO logs to the standard output (to be captured by the GUI console).
    """
    # Create region-specific subfolders to keep log files organized
    log_dir = BASE_LOG_DIR / region_code
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{script_name}.log"

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.DEBUG) 
    
    # Clear existing handlers to prevent duplicate log lines 
    # This is crucial when running multiple pipeline tasks in the same GUI session
    if logger.hasHandlers():
        logger.handlers.clear()

    # File Handler: Captures deep execution details (DEBUG level and above)
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG) 
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console Handler: Streams user-friendly messages (INFO level and above) to the UI
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) 
    console_formatter = logging.Formatter('>>> %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Suppress overly verbose third-party logs so they don't spam our custom log files
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger