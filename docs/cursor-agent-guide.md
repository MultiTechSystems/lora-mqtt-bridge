# Developing Custom Python Applications for MultiTech Conduit with Cursor Agent

This guide provides example prompts and templates for using Cursor Agent to develop custom Python applications for MultiTech Conduit gateways.

> **Note:** Technical requirements, deployment commands, and coding standards are maintained in `.cursor/rules/`. This guide focuses on example prompts and implementation patterns.

## Example Prompts

### Create New Project

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

### Create Configuration Models

```
Create configuration models using Python dataclasses with from_dict() class methods for JSON loading.

Requirements:
- No external dependencies (no pydantic)
- Type hints compatible with Python 3.8 (use typing.Optional, typing.List, typing.Dict)
- Nested configuration support
- Default values for all optional fields
- Validation in from_dict() methods where needed
```

### Create MQTT Client

```
Create an MQTT client that works with paho-mqtt on mLinux.

Requirements:
- Support both paho-mqtt 1.x and 2.x APIs
- TLS/SSL support with certificate configuration
- Automatic reconnection with exponential backoff
- Message queuing when disconnected
- Thread-safe operation
```

### Convert to Python 3.8

```
Convert this code to be Python 3.8 compatible:

Requirements:
- Replace `list[str]` with `List[str]` from typing
- Replace `dict[str, Any]` with `Dict[str, Any]` from typing
- Replace `str | None` with `Optional[str]`
- Replace `X | Y` union types with `Union[X, Y]`
- Add `from __future__ import annotations` at top of files
```

### Create Build Script

```
Create a build-tarball.sh script for mLinux app deployment.

Requirements:
- Create tarball with: src/, requirements.txt, start script
- Include manifest.json for app-manager
- Set correct permissions
- Name format: {app_name}-{version}-mlinux{6|7}.tar.gz
```

### Create Test Suite

```
Create pytest tests for the application.

Requirements:
- Use pytest fixtures for common setup
- Mock MQTT clients for unit tests
- Test configuration loading from dict and file
- Test message filtering logic
- No pydantic or external validation dependencies
```

### Fuzz Testing

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

### Synchronize Platform Versions

```
Synchronize the mlinux-6 and ubuntu implementations with the latest changes from mlinux-7.

Requirements:
- Copy all source files
- Adjust Python 3.8 type hints for mlinux-6
- Keep Python 3.10+ syntax for mlinux-7 and ubuntu
- Rebuild tarballs after sync
- Run tests on all versions
```

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
- IP: [gateway IP]
- mLinux version: [6 or 7]
- App location: /var/config/app/[app_name]

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

## Implementation Patterns

### Status Writer

Example implementation for app-manager status reporting:

```python
import json
import os
import threading
from datetime import datetime


class StatusWriter:
    """Write status.json for mLinux app-manager integration."""

    def __init__(self, app_dir: str | None = None, update_interval: float = 10.0):
        self.app_dir = app_dir if app_dir else (os.getenv("APP_DIR") or ".")
        self.status_file = os.path.join(self.app_dir, "status.json")
        self.update_interval = update_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._status_info = "Starting..."

    def start(self) -> None:
        """Start background status update thread."""
        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background thread and write final status."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self._write_status("Stopped")

    def set_status(self, info: str) -> None:
        """Update the status info (thread-safe)."""
        with self._lock:
            self._status_info = info

    def _update_loop(self) -> None:
        """Background loop to periodically write status."""
        while self._running:
            with self._lock:
                info = self._status_info
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._write_status(f"{info} @ {timestamp}")
            threading.Event().wait(self.update_interval)

    def _write_status(self, app_info: str) -> None:
        """Write status.json atomically."""
        status_data = {"pid": os.getpid(), "AppInfo": app_info[:160]}
        temp_file = self.status_file + ".tmp"
        try:
            with open(temp_file, "w") as f:
                json.dump(status_data, f)
            os.replace(temp_file, self.status_file)
        except OSError:
            pass  # Ignore write errors
```

Status format example: `Local:OK | Remote:1/2 | Msgs:42 @ 14:30:00`

### App Manifest (manifest.json)

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
