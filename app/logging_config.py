"""
Centralized logging configuration for the application.
Logs to both console and file in /app/log directory.
"""
import logging
import logging.handlers
import os
from pathlib import Path

# Log directory - use environment variable or default to /app/log
LOG_DIR = Path(os.environ.get("LOG_DIR", "/app/log"))
LOG_DIR.mkdir(exist_ok=True, parents=True)

# Log files
API_LOG_FILE = LOG_DIR / "api.log"
APP_LOG_FILE = LOG_DIR / "app.log"
ERROR_LOG_FILE = LOG_DIR / "errors.log"

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"


def setup_logging(service_name: str = "api") -> None:
    """
    Setup centralized logging for the application.

    Args:
        service_name: Name of the service ("api", "bot", or other)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Main log file handler (all logs)
    app_file_handler = logging.handlers.RotatingFileHandler(
        APP_LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,  # Keep 5 backups
        encoding="utf-8"
    )
    app_file_handler.setLevel(logging.DEBUG)
    app_file_formatter = logging.Formatter(DETAILED_FORMAT)
    app_file_handler.setFormatter(app_file_formatter)
    root_logger.addHandler(app_file_handler)

    # Error log file handler (errors only)
    error_file_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_formatter = logging.Formatter(DETAILED_FORMAT)
    error_file_handler.setFormatter(error_file_formatter)
    root_logger.addHandler(error_file_handler)

    # Service-specific log file handler
    service_log_file = LOG_DIR / f"{service_name}.log"
    service_file_handler = logging.handlers.RotatingFileHandler(
        service_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    service_file_handler.setLevel(logging.DEBUG)
    service_file_formatter = logging.Formatter(DETAILED_FORMAT)
    service_file_handler.setFormatter(service_file_formatter)
    root_logger.addHandler(service_file_handler)

    # Log initialization message
    root_logger.info("=" * 80)
    root_logger.info("Logging initialized for service: %s", service_name)
    root_logger.info("Log directory: %s", LOG_DIR)
    root_logger.info("Log files: app.log, errors.log, %s.log", service_name)
    root_logger.info("=" * 80)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
