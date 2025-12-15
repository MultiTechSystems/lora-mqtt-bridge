# Developing Custom Python Applications for MultiTech Conduit with Cursor Agent

This guide documents best practices and prompts for using Cursor Agent (Claude) to develop custom Python applications for MultiTech Conduit gateways, based on lessons learned from the LoRa MQTT Bridge project.

## Overview

MultiTech Conduit gateways run mLinux, a custom Linux distribution with specific constraints:
- **mLinux 6.x**: Python 3.8 (limited package availability)
- **mLinux 7.x**: Python 3.10 (better package support, but still constrained)

The gateway's app-manager system provides a standardized way to deploy, manage, and monitor custom applications.

## Project Structure

### Recommended Directory Layout

```
my-app/
├── mlinux-6/                    # Python 3.8 compatible version
│   ├── src/my_app/
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── build-tarball.sh
├── mlinux-7/                    # Python 3.10 compatible version
│   ├── src/my_app/
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── build-tarball.sh
├── ubuntu/                      # Development/server version
│   ├── src/my_app/
│   └── ...
├── src/                         # Main development source (Python 3.10+)
│   └── my_app/
├── tests/
├── docs/
├── config/
│   └── example-config.json
├── dist/                        # Built tarballs
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Initial Project Setup Prompts

### 1. Create Project Scaffold

```
Create a Python application for MultiTech Conduit gateways that [describe your application].

Requirements:
- Support both mLinux 6 (Python 3.8) and mLinux 7 (Python 3.10)
- Use dataclasses for configuration (no pydantic - not available on mLinux)
- Include JSON-based configuration file support
- Add syslog logging for mLinux compatibility
- Create status.json writer for app-manager integration
- Structure code with separate directories for mlinux-6, mlinux-7, and ubuntu/development
```

### 2. Configuration Models

```
Create configuration models using Python dataclasses with from_dict() class methods for JSON loading.

Requirements:
- No external dependencies (no pydantic)
- Type hints compatible with Python 3.8 (use typing.Optional, typing.List, typing.Dict)
- Nested configuration support
- Default values for all optional fields
- Validation in from_dict() methods where needed
```

### 3. MQTT Client Implementation

```
Create an MQTT client that works with paho-mqtt on mLinux.

Requirements:
- Support both paho-mqtt 1.x and 2.x APIs
- TLS/SSL support with certificate configuration
- Automatic reconnection with exponential backoff
- Message queuing when disconnected
- Thread-safe operation
```

## Python Version Compatibility Prompts

### For mLinux 6 (Python 3.8)

```
Convert this code to be Python 3.8 compatible:

Requirements:
- Replace `list[str]` with `List[str]` from typing
- Replace `dict[str, Any]` with `Dict[str, Any]` from typing
- Replace `str | None` with `Optional[str]`
- Replace `X | Y` union types with `Union[X, Y]`
- Add `from __future__ import annotations` at top of files
- Use `# type: List[str]` comments for variable annotations if needed
```

### Type Hint Conversion Table

| Python 3.10+ | Python 3.8 |
|--------------|------------|
| `list[str]` | `List[str]` |
| `dict[str, Any]` | `Dict[str, Any]` |
| `str \| None` | `Optional[str]` |
| `int \| str` | `Union[int, str]` |
| `tuple[int, str]` | `Tuple[int, str]` |

## Gateway-Specific Features

### 1. Gateway UUID Retrieval

```
Create a utility function to retrieve the MultiTech gateway UUID.

Requirements:
- Read from /sys/devices/platform/mts-io/uuid (primary)
- Fallback to /sys/class/dmi/id/product_uuid
- Fallback to mts-io-sysfs command
- Format UUID as lowercase with dashes (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
- Cache the result (use @lru_cache)
- Return a default UUID if all methods fail
```

### 2. Status Writer for App-Manager

```
Create a status writer that outputs status.json for mLinux app-manager.

Requirements:
- Write to $APP_DIR/status.json (use APP_DIR environment variable)
- Include fields: pid (integer), AppInfo (string, max 160 chars)
- Update periodically in background thread (e.g., every 10 seconds)
- Thread-safe status updates
- Write atomically (write to .tmp file, then rename)
- Graceful shutdown with final status write
```

Example status.json format:
```json
{"pid": 12345, "AppInfo": "Local:OK | Remote:1/1 | Msgs:42 @ 14:30:00"}
```

**Important**: The `pid` field must be an integer (not a string) for app-manager to correctly track the process.

Status format: `Local:{OK|DISC} | Remote:{connected}/{total} [| Msgs:{count}] @ {time}`

Example implementation pattern:
```python
class StatusWriter:
    def __init__(self, app_dir: str | None = None, update_interval: float = 10.0):
        self.app_dir = app_dir if app_dir else (os.getenv("APP_DIR") or ".")
        self.status_file = os.path.join(self.app_dir, "status.json")
        self._running = False
        self._thread: threading.Thread | None = None
        
    def start(self) -> None:
        """Start background status update thread."""
        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()
        
    def _write_status(self, app_info: str) -> None:
        """Write status.json atomically."""
        status_data = {"pid": os.getpid(), "AppInfo": app_info[:160]}
        temp_file = self.status_file + ".tmp"
        with open(temp_file, "w") as f:
            json.dump(status_data, f)
        os.replace(temp_file, self.status_file)
```

### 3. Syslog Logging

```
Configure Python logging to output to syslog on mLinux.

Requirements:
- Use SysLogHandler for mLinux deployment
- Fall back to StreamHandler for development
- Include app name in syslog ident
- Support log level configuration
- Format: timestamp - logger - level - message
```

## Build and Deployment Prompts

### 1. Create Build Script

```
Create a build-tarball.sh script for mLinux app deployment.

Requirements:
- Create tarball with: src/, requirements.txt, start script
- Include app.json manifest for app-manager
- Set correct permissions
- Name format: {app_name}-{version}-mlinux{6|7}.tar.gz
```

### 2. App Manifest (app.json)

```json
{
  "name": "my-app",
  "version": "1.0.0",
  "description": "My custom application",
  "start": "/usr/bin/python3 -m my_app",
  "stop": "",
  "restart": "always",
  "config": {
    "file": "config/config.json"
  }
}
```

### 3. Deploy to Gateway

```
Deploy the application to a MultiTech gateway.

Gateway: 172.16.33.111
Credentials: admin/admin2019!

Steps:
1. Copy tarball via SCP
2. Use gateway web API for installation:
   - POST /api/file/customApps (upload)
   - POST /api/customApps (install)
3. Update config if needed
4. Start application via API
```

## Testing Prompts

### 1. Create Test Suite

```
Create pytest tests for the application.

Requirements:
- Use pytest fixtures for common setup
- Mock MQTT clients for unit tests
- Test configuration loading from dict and file
- Test message filtering logic
- No pydantic or external validation dependencies
```

### 2. Fuzz Testing

```
Create fuzz tests for message handling.

Test cases:
- Empty payloads
- Invalid JSON
- Missing required fields
- Unexpected field types (int instead of string)
- Null values
- Very large payloads
- Unicode and special characters
```

## CI/CD Prompts

### 1. GitHub Actions Workflow

```
Create a GitHub Actions CI workflow.

Requirements:
- Test on Python 3.10, 3.11, 3.12
- Run ruff linter and formatter
- Run mypy type checker
- Run pytest with coverage
- Build package
- Use actions/checkout@v4, actions/setup-python@v5, actions/upload-artifact@v4
```

### 2. Fix Linting Errors

```
Run ruff check and fix any errors.

Common issues:
- F401: Unused imports
- E501: Line too long (break into multiple lines)
- B904: Use `raise ... from err` in except blocks
- D401: Docstrings should be imperative mood
- I001: Import sorting
```

## Common Issues and Solutions

### 1. No pydantic on mLinux

**Problem**: pydantic is not available and pip may not work on mLinux.

**Solution**: Use dataclasses with manual `from_dict()` methods:

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class MyConfig:
    name: str = ""
    enabled: bool = True
    items: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MyConfig":
        return cls(
            name=data.get("name", ""),
            enabled=data.get("enabled", True),
            items=data.get("items", []),
        )
```

### 2. paho-mqtt Version Compatibility

**Problem**: mLinux may have paho-mqtt 1.x, but development uses 2.x.

**Solution**: Handle both APIs:

```python
def _create_client(self) -> mqtt.Client:
    try:
        # paho-mqtt 2.x
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,  # type: ignore
            client_id=self.client_id,
        )
    except (TypeError, AttributeError):
        # paho-mqtt 1.x fallback
        client = mqtt.Client(client_id=self.client_id)
    return client
```

### 3. App-Manager Lock Issues

**Problem**: `Failed to acquire lock on file` when using app-manager.

**Solution**: Use the web API instead of CLI, or remove stale lock files:
```bash
rm /var/run/AppManager.lock
```

### 4. Configuration Overwritten on Install

**Problem**: App installation overwrites custom configuration.

**Solution**: After `app_install`, write config to `/var/config/app/{app_name}/config/config.json` and restart the app.

## Synchronizing Platform Versions

```
Synchronize the mlinux-6 and ubuntu implementations with the latest changes from mlinux-7.

Requirements:
- Copy all source files
- Adjust Python 3.8 type hints for mlinux-6
- Keep Python 3.10+ syntax for mlinux-7 and ubuntu
- Rebuild tarballs after sync
- Run tests on all versions
```

## Example Prompts for Specific Tasks

### Add a New Feature

```
Add [feature description] to the application.

Requirements:
- Implement in mlinux-7/src first
- Add configuration options to config.py
- Add tests
- Update documentation
- Sync to mlinux-6 (Python 3.8) and ubuntu versions
- Rebuild tarballs
```

### Debug Gateway Issues

```
The application on the gateway shows this error: [error message]

Gateway details:
- IP: 172.16.33.111
- mLinux version: 7
- App location: /var/config/app/my_app

Please:
1. Check the application logs via SSH
2. Identify the root cause
3. Propose a fix
4. Test the fix
5. Deploy the updated application
```

### Create Release

```
Create a new release for version X.Y.Z.

Steps:
1. Update version in pyproject.toml files
2. Rebuild all tarballs
3. Run full test suite
4. Create git tag with release notes
5. Push tag to GitHub
6. Create GitHub release with changelog
```

## Best Practices Summary

1. **Always test on actual gateway hardware** - Emulation doesn't catch all issues
2. **Use dataclasses, not pydantic** - Minimize dependencies for mLinux
3. **Support multiple Python versions** - Maintain separate mlinux-6/7 directories
4. **Write comprehensive tests** - Especially for edge cases and error handling
5. **Use the web API for deployment** - More reliable than app-manager CLI
6. **Log to syslog** - Integrates with mLinux logging infrastructure
7. **Write status.json** - Required for app-manager monitoring
8. **Cache expensive operations** - Like gateway UUID retrieval
9. **Handle reconnection gracefully** - Network interruptions are common
10. **Document configuration options** - Users need clear examples
