"""
Project-local Python startup hooks.

Python imports ``sitecustomize`` automatically on startup (when present on
``sys.path``). We use this to enforce macOS fork safety for RQ workers.
"""

from __future__ import annotations

import os
import platform


def _enable_macos_objc_fork_safety_workaround() -> None:
    """
    Prevent Objective-C runtime crashes in forked RQ workhorses on macOS.

    RQ executes each job in a forked child process; when Objective-C-backed
    libraries are initialized in a multi-threaded parent, macOS can abort the
    child with ``objc_initializeAfterForkError`` unless this flag is set.
    """

    if platform.system() != "Darwin":
        return
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")


_enable_macos_objc_fork_safety_workaround()

