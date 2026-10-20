"""Console script: runs the bundled `wasm-tools` with the command line it was given."""

from __future__ import annotations

import subprocess
import sys
from typing import NoReturn

from . import get_executable


def _exec(argv: list[str]) -> NoReturn:
    try:
        path = get_executable()
    except (KeyError, FileNotFoundError) as exc:
        sys.exit(f"wasm-tools: {exc}")
    sys.exit(subprocess.call([str(path), *argv]))


def main(argv: list[str] | None = None) -> NoReturn:
    """`python -m wasm_tools_package [ARGS...]`: the same as `wasm-tools [ARGS...]`."""
    _exec(sys.argv[1:] if argv is None else argv)


def wasm_tools() -> NoReturn:
    _exec(sys.argv[1:])
