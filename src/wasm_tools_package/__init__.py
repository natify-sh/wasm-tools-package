"""wasm-tools, the Bytecode Alliance's WebAssembly toolkit, as a package: the prebuilt executable.

    import wasm_tools_package as wasm_tools

    wasm_tools.run("parse", "in.wat", "-o", "out.wasm")
    wasm_tools.get_executable()          # pathlib.Path of the bundled wasm-tools
    wasm_tools.wasm_tools_version()      # "1.262.0"

The executable is also installed as the console script `wasm-tools`, and `python -m wasm_tools_package <subcommand> ...`
runs it. An unofficial redistribution of https://github.com/bytecodealliance/wasm-tools (Apache-2.0 WITH LLVM-exception,
Apache-2.0 or MIT).
"""

from __future__ import annotations

import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

__all__ = ["TOOLS", "bin_dir", "get_executable", "run", "wasm_tools_version"]

# The executables of the pinned wasm-tools release that the wheel carries (see build_wasm_tools.py).
TOOLS: tuple[str, ...] = ("wasm-tools",)

_PACKAGE_DIR = Path(__file__).resolve().parent
_EXE_SUFFIX = ".exe" if sys.platform == "win32" else ""


@lru_cache(maxsize=1)
def wasm_tools_version() -> str:
    """The version of wasm-tools this executable was built from (the first three numbers of this package's version)."""
    return (_PACKAGE_DIR / "_wasm_tools_version.txt").read_text(encoding="utf-8").strip()


def bin_dir() -> Path:
    """The directory with the executable."""
    return _PACKAGE_DIR / "bin"


def get_executable(name: str = "wasm-tools") -> Path:
    """The path of the bundled executable `name` (one of `TOOLS`); `KeyError` for any other name."""
    if name not in TOOLS:
        raise KeyError(f"{name!r} is not a tool of this package; one of: {', '.join(TOOLS)}")
    path = bin_dir() / (name + _EXE_SUFFIX)
    if not path.is_file():
        raise FileNotFoundError(f"{path} is missing: the package was built without it")
    if sys.platform != "win32" and not os.access(path, os.X_OK):  # a wheel that lost the mode bits
        try:
            path.chmod(path.stat().st_mode | 0o111)
        except OSError:
            pass  # a read-only install: let the caller's own run fail with a clear message
    return path


def run(*args: str | os.PathLike[str], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
    """Run `wasm-tools` with `args` (a subcommand first: `run("validate", "a.wasm")`); `kwargs` go to `subprocess.run`
    (`check=True` unless given)."""
    check = kwargs.pop("check", True)
    cmd = [str(get_executable()), *[os.fspath(a) for a in args]]
    return cast("subprocess.CompletedProcess[Any]", subprocess.run(cmd, check=check, **kwargs))
