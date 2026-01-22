#!/usr/bin/env python3
"""
Structured Logging Module

Provides centralized logging with:
- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- File rotation (daily logs, keep 30 days)
- Structured JSON logging option
- Performance logging
- Error tracking
"""
import os
import sys
import json
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps
import time

# =============================================================================
# CONFIGURATION
# =============================================================================

LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get("LOG_FORMAT", "structured")  # "structured" or "simple"
LOG_TO_FILE = os.environ.get("LOG_TO_FILE", "true").lower() == "true"
LOG_TO_CONSOLE = os.environ.get("LOG_TO_CONSOLE", "true").lower() == "true"
LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", "10485760"))  # 10MB
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", "5"))
LOG_ROTATE_WHEN = os.environ.get("LOG_ROTATE_WHEN", "midnight")  # midnight, D, H
LOG_INTERVAL = int(os.environ.get("LOG_INTERVAL", "1"))  # days

# =============================================================================
# LOGGER SETUP
# =============================================================================

def setup_logger(name: str = "pokemon_agent", level: str = None) -> logging.Logger:
    """
    Set up a logger with file rotation and console output.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    # Don't add handlers if already configured
    if logger.handlers:
        return logger
    
    # Set log level
    log_level = getattr(logging, level or LOG_LEVEL, logging.INFO)
    logger.setLevel(log_level)
    
    # Create formatters
    if LOG_FORMAT == "structured":
        formatter = StructuredFormatter()
        console_formatter = SimpleFormatter()  # Simpler for console
    else:
        formatter = SimpleFormatter()
        console_formatter = SimpleFormatter()
    
    # File handler with rotation
    if LOG_TO_FILE:
        # Use timed rotation (daily by default)
        file_handler = TimedRotatingFileHandler(
            filename=LOG_DIR / f"{name}.log",
            when=LOG_ROTATE_WHEN,
            interval=LOG_INTERVAL,
            backupCount=30,  # Keep 30 days of logs
            encoding='utf-8',
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Separate error log
        error_handler = TimedRotatingFileHandler(
            filename=LOG_DIR / f"{name}_errors.log",
            when=LOG_ROTATE_WHEN,
            interval=LOG_INTERVAL,
            backupCount=30,
            encoding='utf-8',
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    # Console handler
    if LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


# =============================================================================
# FORMATTERS
# =============================================================================

class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter for better parsing."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        return json.dumps(log_data, default=str)


class SimpleFormatter(logging.Formatter):
    """Simple human-readable log formatter."""
    
    def __init__(self):
        super().__init__(
            fmt='[%(asctime)s] %(levelname)-8s %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


# =============================================================================
# PERFORMANCE LOGGING
# =============================================================================

def log_performance(func):
    """Decorator to log function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            logger.info(
                f"{func.__name__} completed",
                extra={
                    "function": func.__name__,
                    "duration_seconds": round(duration, 3),
                    "status": "success",
                }
            )
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"{func.__name__} failed: {str(e)}",
                extra={
                    "function": func.__name__,
                    "duration_seconds": round(duration, 3),
                    "status": "error",
                    "error": str(e),
                },
                exc_info=True
            )
            raise
    
    return wrapper


# =============================================================================
# ERROR TRACKING
# =============================================================================

class ErrorTracker:
    """Track errors for monitoring and alerting."""
    
    def __init__(self):
        self.errors: list = []
        self.max_errors = 1000  # Keep last 1000 errors
    
    def record_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        logger: logging.Logger = None
    ):
        """Record an error with context."""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
        }
        
        self.errors.append(error_data)
        
        # Keep only recent errors
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        # Log if logger provided
        if logger:
            logger.error(
                f"Error: {error_data['error_type']}: {error_data['error_message']}",
                extra=error_data,
                exc_info=True
            )
    
    def get_error_summary(self, last_n: int = 100) -> Dict[str, Any]:
        """Get summary of recent errors."""
        recent_errors = self.errors[-last_n:]
        
        error_counts = {}
        for error in recent_errors:
            error_type = error["error_type"]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            "total_errors": len(recent_errors),
            "error_types": error_counts,
            "recent_errors": recent_errors[-10:],  # Last 10 errors
        }


# Global error tracker
_error_tracker = ErrorTracker()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global logger instance
_logger: Optional[logging.Logger] = None

def get_logger(name: str = "pokemon_agent") -> logging.Logger:
    """Get or create global logger."""
    global _logger
    if _logger is None:
        _logger = setup_logger(name)
    return _logger


def log_info(message: str, **kwargs):
    """Log info message with extra fields."""
    get_logger().info(message, extra=kwargs)


def log_warning(message: str, **kwargs):
    """Log warning message with extra fields."""
    get_logger().warning(message, extra=kwargs)


def log_error(message: str, error: Exception = None, **kwargs):
    """Log error message with extra fields."""
    logger = get_logger()
    
    if error:
        _error_tracker.record_error(error, context=kwargs, logger=logger)
        logger.error(message, extra=kwargs, exc_info=True)
    else:
        logger.error(message, extra=kwargs)


def log_debug(message: str, **kwargs):
    """Log debug message with extra fields."""
    get_logger().debug(message, extra=kwargs)


def get_error_summary() -> Dict[str, Any]:
    """Get error summary for monitoring."""
    return _error_tracker.get_error_summary()


# =============================================================================
# INITIALIZE
# =============================================================================

# Initialize logger on import
get_logger()
