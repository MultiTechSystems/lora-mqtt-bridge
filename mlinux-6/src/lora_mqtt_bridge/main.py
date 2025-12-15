#!/usr/bin/env python3
"""Main entry point for the LoRa MQTT Bridge application.

This module provides the main entry point and CLI interface
for the MQTT bridge application.

Compatible with Python 3.8+ (mLinux 6.3.5)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from lora_mqtt_bridge import __version__
from lora_mqtt_bridge.bridge import MQTTBridge
from lora_mqtt_bridge.utils.config_loader import load_config, load_config_from_env
from lora_mqtt_bridge.utils.logging_setup import setup_logging

if TYPE_CHECKING:
    from lora_mqtt_bridge.models.config import BridgeConfig


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        prog="lora-mqtt-bridge",
        description="Bridge MQTT messages from local LoRaWAN gateway to remote brokers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -c config.json
  %(prog)s --env
  %(prog)s -c config.json --log-level DEBUG

Environment Variables:
  LORA_MQTT_BRIDGE_LOCAL_HOST       Local broker hostname
  LORA_MQTT_BRIDGE_LOCAL_PORT       Local broker port
  LORA_MQTT_BRIDGE_REMOTE_HOST      Remote broker hostname
  LORA_MQTT_BRIDGE_REMOTE_BROKERS   JSON array of remote broker configs
        """,
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Path to configuration file (JSON)",
    )
    parser.add_argument(
        "--env",
        action="store_true",
        help="Load configuration from environment variables",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser.parse_args()


def load_configuration(args: argparse.Namespace) -> BridgeConfig:
    """Load configuration based on command line arguments.

    Args:
        args: Parsed command line arguments.

    Returns:
        The loaded configuration.

    Raises:
        SystemExit: If configuration cannot be loaded.
    """
    config = None  # type: Optional[BridgeConfig]

    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error("Configuration file not found: %s", config_path)
            sys.exit(1)

        try:
            config = load_config(str(config_path))
            logger.info("Loaded configuration from %s", config_path)
        except Exception as e:
            logger.error("Failed to load configuration: %s", e)
            sys.exit(1)

    elif args.env:
        try:
            config = load_config_from_env()
            logger.info("Loaded configuration from environment variables")
        except Exception as e:
            logger.error("Failed to load configuration from environment: %s", e)
            sys.exit(1)

    else:
        # Try default config paths
        default_paths = [
            Path("config.json"),
            Path("/etc/lora-mqtt-bridge/config.json"),
            Path.home() / ".config" / "lora-mqtt-bridge" / "config.json",
        ]

        for path in default_paths:
            if path.exists():
                try:
                    config = load_config(str(path))
                    logger.info("Loaded configuration from %s", path)
                    break
                except Exception:
                    continue

        if config is None:
            # Fall back to environment variables
            try:
                config = load_config_from_env()
                logger.info("Loaded configuration from environment variables")
            except Exception:
                logger.error(
                    "No configuration found. Specify --config or --env, "
                    "or create a config.json file."
                )
                sys.exit(1)

    # Apply command line overrides
    if args.log_level:
        config.log.level = args.log_level
    if args.log_file:
        config.log.file = args.log_file

    return config


def validate_config(config: BridgeConfig) -> bool:
    """Validate the configuration.

    Args:
        config: The configuration to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not config.remote_brokers:
        logger.warning("No remote brokers configured")

    enabled_brokers = [b for b in config.remote_brokers if b.enabled]
    if not enabled_brokers:
        logger.warning("No enabled remote brokers")

    return True


def main() -> int:
    """Run the MQTT bridge application.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    # Parse arguments first to get log level
    args = parse_args()

    # Set up initial logging
    from lora_mqtt_bridge.models.config import LogConfig

    log_config = LogConfig(
        level=args.log_level,
        file=args.log_file,
    )
    setup_logging(log_config)

    logger.info("LoRa MQTT Bridge v%s starting", __version__)

    # Load configuration
    config = load_configuration(args)

    # Update logging with config settings
    setup_logging(config.log)

    # Validate configuration
    if not validate_config(config):
        logger.error("Invalid configuration")
        return 1

    # Create and run bridge
    bridge = MQTTBridge(config)

    try:
        bridge.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception:
        logger.exception("Unexpected error")
        return 1

    logger.info("LoRa MQTT Bridge stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
