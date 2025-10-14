"""
Logging configuration for the e-commerce analytics pipeline.
Provides structured logging with different levels and formatters.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color coding for different log levels."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        """Format log record with colors."""
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Add color to level name
        record.levelname = f"{log_color}{record.levelname}{reset_color}"
        
        return super().format(record)


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: str = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    Set up a logger with console and optional file handlers.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level
        log_file: Optional log file path
        use_colors: Whether to use colored output
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if use_colors:
        console_format = ColoredFormatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_format = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with default configuration.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return setup_logger(name)


# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Main application logger
app_logger = setup_logger(
    "ecommerce_analytics",
    level=logging.INFO,
    log_file=f"logs/app_{datetime.now().strftime('%Y%m%d')}.log"
)


