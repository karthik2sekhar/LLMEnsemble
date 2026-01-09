"""
Logging configuration and utilities.
Provides structured logging with configurable levels and formats.
"""

import logging
import sys
from datetime import datetime
from typing import Optional

from ..config import get_settings

settings = get_settings()

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Custom log levels
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output."""
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
        "TRACE": "\033[90m",     # Gray
    }
    RESET = "\033[0m"
    
    def format(self, record):
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: Optional[str] = None,
    use_colors: bool = True,
) -> None:
    """
    Set up logging configuration for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_colors: Whether to use colored output
    """
    log_level = level or settings.log_level
    
    # Get the numeric level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Use colored formatter in debug mode or if colors enabled
    if settings.debug and use_colors:
        formatter = ColoredFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    else:
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: The module name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class RequestLogger:
    """Context manager for logging request/response details."""
    
    def __init__(self, logger: logging.Logger, operation: str):
        """
        Initialize request logger.
        
        Args:
            logger: Logger instance to use
            operation: Name of the operation being performed
        """
        self.logger = logger
        self.operation = operation
        self.start_time: Optional[datetime] = None
        self.extra_data: dict = {}
    
    def __enter__(self):
        """Start logging the request."""
        self.start_time = datetime.utcnow()
        self.logger.debug(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log the result of the request."""
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(
                f"Failed {self.operation} after {duration:.3f}s: {exc_val}",
                exc_info=True
            )
        else:
            self.logger.info(f"Completed {self.operation} in {duration:.3f}s")
        
        return False  # Don't suppress exceptions
    
    def add_data(self, **kwargs):
        """Add extra data to be logged."""
        self.extra_data.update(kwargs)


def log_api_call(
    logger: logging.Logger,
    model: str,
    tokens: int,
    cost: float,
    duration: float,
    cached: bool = False,
    error: Optional[str] = None,
) -> None:
    """
    Log an API call with standardized format.
    
    Args:
        logger: Logger instance
        model: Model that was called
        tokens: Number of tokens used
        cost: Cost of the call
        duration: Duration in seconds
        cached: Whether the response was cached
        error: Error message if the call failed
    """
    status = "CACHED" if cached else ("ERROR" if error else "SUCCESS")
    
    log_message = (
        f"API Call [{status}] - "
        f"Model: {model} | "
        f"Tokens: {tokens} | "
        f"Cost: ${cost:.4f} | "
        f"Duration: {duration:.2f}s"
    )
    
    if error:
        log_message += f" | Error: {error}"
        logger.error(log_message)
    else:
        logger.info(log_message)
