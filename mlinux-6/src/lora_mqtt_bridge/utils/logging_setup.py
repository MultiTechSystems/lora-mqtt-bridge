"""Logging setup utilities.

This module provides functions for configuring logging
for the LoRa MQTT Bridge application.

Compatible with Python 3.8+ (mLinux 6.3.5)
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from lora_mqtt_bridge.models.config import LogConfig


def setup_logging(config: Optional["LogConfig"] = None) -> logging.Logger:
    """Set up logging for the application.

    Args:
        config: Optional logging configuration.

    Returns:
        The configured root logger.
    """
    # Default configuration
    level_str = "INFO"
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file = None  # type: Optional[str]

    if config:
        level_str = config.level
        log_format = config.format
        log_file = config.file

    # Parse log level
    level = getattr(logging, level_str.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%dT%H:%M:%S%z")

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if configured
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Try to add syslog handler on Linux
    try:
        syslog_handler = logging.handlers.SysLogHandler(address="/dev/log")
        syslog_handler.ident = "lora-mqtt-bridge: "
        syslog_handler.setLevel(level)
        syslog_handler.setFormatter(formatter)
        root_logger.addHandler(syslog_handler)
    except (FileNotFoundError, OSError):
        # Syslog not available on this system
        pass

    # Set levels for noisy libraries
    logging.getLogger("paho.mqtt").setLevel(logging.WARNING)

    logger = logging.getLogger("lora_mqtt_bridge")
    logger.info("Logging configured at level %s", level_str)

    return logger
