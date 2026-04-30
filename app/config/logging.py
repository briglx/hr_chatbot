"""Logging configuration for the HR chatbot application."""

import logging
from logging.handlers import RotatingFileHandler
import sys

import structlog


def setup_logging(log_file_path: str = "hr_chatbot.log"):
    """Set up logging with structlog, including a rotating file handler and console output."""
    # Create a rotating file handler (logs to a file with rotation)
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,  # 10 MB per file, 5 backups
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(message)s"))

    # Create a console handler (logs to the console)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    # Configure the root logger to use both handlers
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler],
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # Merges contextvars (e.g., trace_id)
            structlog.processors.add_log_level,  # Adds log level (info, error)
            structlog.processors.TimeStamper(fmt="iso"),  # Adds a timestamp
            # Use ConsoleRenderer for console logs (colorized) and JSONRenderer for file logs
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Use different renderers for console and file handlers
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),  # JSON for file logs
        foreign_pre_chain=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
        ],
    )
    file_handler.setFormatter(formatter)  # JSON logs for files
    console_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer()
        )  # Colorized logs for console
    )
