"""System information utilities.

This module provides functions for retrieving system information
such as the gateway UUID.
"""

from __future__ import annotations

import logging
import subprocess
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Possible locations for UUID on mLinux systems
UUID_PATHS = [
    "/sys/devices/platform/mts-io/uuid",
    "/sys/class/dmi/id/product_uuid",
]


def _format_uuid(uuid_raw: str) -> str:
    """Format a raw UUID string to standard format with dashes.

    Converts "244AB1FBB08D1DCCD02DBEE6F5236CED" to
    "244ab1fb-b08d-1dcc-d02d-bee6f5236ced"

    Args:
        uuid_raw: Raw UUID string (32 hex characters).

    Returns:
        Formatted UUID string with dashes.
    """
    uuid_clean = uuid_raw.strip().lower().replace("-", "")
    if len(uuid_clean) != 32:
        logger.warning("UUID has unexpected length: %d", len(uuid_clean))
        return uuid_raw.lower()

    # Format as 8-4-4-4-12
    return f"{uuid_clean[:8]}-{uuid_clean[8:12]}-{uuid_clean[12:16]}-{uuid_clean[16:20]}-{uuid_clean[20:]}"


@lru_cache(maxsize=1)
def get_gateway_uuid() -> str:
    """Get the gateway UUID from the system.

    Tries multiple methods to retrieve the UUID:
    1. Read from sysfs paths
    2. Use mts-io-sysfs command
    3. Fall back to a default value

    Returns:
        The formatted gateway UUID string.
    """
    # Try reading from sysfs paths
    for path_str in UUID_PATHS:
        path = Path(path_str)
        if path.exists():
            try:
                uuid_raw = path.read_text().strip()
                if uuid_raw:
                    formatted = _format_uuid(uuid_raw)
                    logger.info("Got gateway UUID from %s: %s", path_str, formatted)
                    return formatted
            except (OSError, IOError) as e:
                logger.debug("Failed to read UUID from %s: %s", path_str, e)

    # Try mts-io-sysfs command
    try:
        result = subprocess.run(
            ["mts-io-sysfs", "show", "uuid"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            uuid_raw = result.stdout.strip()
            formatted = _format_uuid(uuid_raw)
            logger.info("Got gateway UUID from mts-io-sysfs: %s", formatted)
            return formatted
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.debug("Failed to get UUID from mts-io-sysfs: %s", e)

    # Fall back to default
    logger.warning("Could not determine gateway UUID, using default")
    return "00000000-0000-0000-0000-000000000000"
