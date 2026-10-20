"""The package as installed: the executable runs, WAT -> wasm -> WAT works, and components can be built."""

from __future__ import annotations

import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import pytest

import wasm_tools_package as wasm_tools

WAT = """
(module
  (func (export "add") (param i32 i32) (result i32)
    local.get 0
    local.get 1
    i32.add))
"""


@pytest.fixture
def add_wasm(tmp_path: Path) -> Path:
    wat = tmp_path / "add.wat"
    wat.write_text(WAT, encoding="utf-8")
    wasm = tmp_path / "add.wasm"
    wasm_tools.run("parse", wat, "-o", wasm)
    return wasm


def test_the_version_is_a_wasm_tools_release() -> None:
    parts = wasm_tools.wasm_tools_version().split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts), wasm_tools.wasm_tools_version()


def test_the_distribution_version_starts_with_the_wasm_tools_version() -> None:
    version = metadata.version("wasm-tools-package")
    if "dev" in version:  # an untagged checkout: setuptools-scm has no tag to take the number from
        pytest.skip(f"{version} is a development version")
    assert version.startswith(wasm_tools.wasm_tools_version() + "."), (version, wasm_tools.wasm_tools_version())


@pytest.mark.parametrize("tool", wasm_tools.TOOLS)
def test_every_tool_runs(tool: str) -> None:
    path = wasm_tools.get_executable(tool)
    assert path.is_file() and path.parent == wasm_tools.bin_dir()
    out = wasm_tools.run("--version", capture_output=True, text=True).stdout.strip()
    assert out.startswith(f"wasm-tools {wasm_tools.wasm_tools_version()}"), out


def test_an_unknown_tool_is_a_key_error() -> None:
    with pytest.raises(KeyError):
        wasm_tools.get_executable("wasm-opt")


def test_the_subcommands_are_all_built() -> None:
    out = wasm_tools.run("help", capture_output=True, text=True).stdout
    for subcommand in ("parse", "print", "validate", "component", "objdump", "strip", "smith", "wast"):
        assert any(line.split()[:1] == [subcommand] for line in out.splitlines()), (subcommand, out)


def test_wasm_roundtrips_through_text(add_wasm: Path) -> None:
    assert add_wasm.read_bytes().startswith(b"\0asm")
    wat = wasm_tools.run("print", add_wasm, capture_output=True, text=True).stdout
    assert '(export "add"' in wat and "i32.add" in wat
    wasm_tools.run("validate", add_wasm)
    objdump = wasm_tools.run("objdump", add_wasm, capture_output=True, text=True).stdout
    assert "code" in objdump and "functions" in objdump


def test_an_invalid_module_fails_validation(tmp_path: Path) -> None:
    bad = tmp_path / "bad.wasm"
    bad.write_bytes(b"\0asm\x01\0\0\0\xff")
    result = wasm_tools.run("validate", bad, check=False, capture_output=True, text=True)
    assert result.returncode != 0 and result.stderr


def test_a_core_module_becomes_a_component(add_wasm: Path, tmp_path: Path) -> None:
    wit = tmp_path / "world.wit"
    wit.write_text(
        "package test:add;\n\nworld adder {\n  export add: func(a: s32, b: s32) -> s32;\n}\n", encoding="utf-8"
    )
    embedded = tmp_path / "embedded.wasm"
    wasm_tools.run("component", "embed", wit, add_wasm, "--world", "adder", "-o", embedded)
    component = tmp_path / "add.component.wasm"
    wasm_tools.run("component", "new", embedded, "-o", component)
    wasm_tools.run("validate", component)
    printed = wasm_tools.run("component", "wit", component, capture_output=True, text=True).stdout
    assert "add: func(a: s32, b: s32) -> s32" in printed, printed


def test_the_console_script_is_installed() -> None:
    found = shutil.which("wasm-tools")
    if found is None:
        pytest.skip("the scripts directory of the environment is not on PATH")
    out = subprocess.run([found, "--version"], check=True, capture_output=True, text=True).stdout.strip()
    assert out.startswith(f"wasm-tools {wasm_tools.wasm_tools_version()}"), out


def test_python_dash_m_runs_the_tool() -> None:
    out = subprocess.run(
        [sys.executable, "-m", "wasm_tools_package", "--version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    assert out.startswith(f"wasm-tools {wasm_tools.wasm_tools_version()}"), out
