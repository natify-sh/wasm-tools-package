"""The executable depends on nothing but the system itself: no C runtime DLL, no library of the build machine.

The wheels run on machines nobody controls, so a tool that quietly depended on a vcruntime or a library of the build machine
would work in CI and fail at the user's. This runs on every platform of the wheel matrix.
"""

from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

import wasm_tools_package as wasm_tools

# What a Linux executable may ask for: the C library and its loader (glibc or musl), and libgcc_s, which Rust's standard library
# unwinds with on glibc (it is part of every glibc system); nothing else.
_LINUX_OK = re.compile(
    r"^(libc\.so\.6|libm\.so\.6|libdl\.so\.2|libpthread\.so\.0|librt\.so\.1|libutil\.so\.1|libgcc_s\.so\.1"
    r"|ld-linux[\w.-]*\.so[\w.]*|ld64\.so[\w.]*|ld-musl-[\w.-]+\.so[\w.]*|libc\.musl-[\w.-]+\.so[\w.]*)$"
)
# macOS: libSystem (and libiconv), which are part of the system and cannot be linked in statically with Apple's toolchain.
_MACOS_OK = re.compile(r"^/usr/lib/(libSystem\.B\.dylib|libiconv\.2\.dylib)$")
# Windows: the C runtime is linked in (+crt-static), so none of its DLLs may be imported.
_WINDOWS_BAD = (b"VCRUNTIME", b"MSVCP", b"api-ms-win-crt", b"ucrtbase")


def _elf_needed(path: Path) -> list[str]:
    """DT_NEEDED of an ELF file, read without readelf (which a test environment may not have)."""
    data = path.read_bytes()
    if data[:4] != b"\x7fELF":
        raise ValueError(f"{path} is not an ELF file")
    is64 = data[4] == 2
    end = "<" if data[5] == 1 else ">"
    if is64:
        (phoff,) = struct.unpack_from(end + "Q", data, 0x20)
        phentsize, phnum = struct.unpack_from(end + "HH", data, 0x36)
    else:
        (phoff,) = struct.unpack_from(end + "I", data, 0x1C)
        phentsize, phnum = struct.unpack_from(end + "HH", data, 0x2A)
    loads: list[tuple[int, int, int]] = []  # (vaddr, offset, filesz)
    dynamic: tuple[int, int] | None = None
    for i in range(phnum):
        base = phoff + i * phentsize
        if is64:
            p_type, _flags, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _align = struct.unpack_from(
                end + "IIQQQQQQ", data, base
            )
        else:
            p_type, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _flags, _align = struct.unpack_from(
                end + "IIIIIIII", data, base
            )
        if p_type == 1:
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == 2:
            dynamic = (p_offset, p_filesz)
    if dynamic is None:
        return []  # a static executable
    needed_offsets: list[int] = []
    strtab = 0
    entry = 16 if is64 else 8
    fmt = end + ("qQ" if is64 else "iI")
    offset, size = dynamic
    for pos in range(offset, offset + size, entry):
        tag, value = struct.unpack_from(fmt, data, pos)
        if tag == 0:
            break
        if tag == 1:
            needed_offsets.append(value)
        elif tag == 5:
            strtab = value
    start = next((o + (strtab - v) for v, o, sz in loads if v <= strtab < v + sz), None)
    if start is None:
        raise ValueError(f"{path}: the string table of the dynamic section was not found")
    names: list[str] = []
    for value in needed_offsets:
        stop = data.index(b"\0", start + value)
        names.append(data[start + value : stop].decode())
    return names


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux executables")
@pytest.mark.parametrize("tool", wasm_tools.TOOLS)
def test_linux_tools_need_only_the_c_library(tool: str) -> None:
    needed = _elf_needed(wasm_tools.get_executable(tool))
    bad = [n for n in needed if not _LINUX_OK.match(n)]
    assert not bad, f"{tool} needs {bad} (all: {needed}): the C library is the only one allowed"


@pytest.mark.skipif(sys.platform != "darwin", reason="Mach-O executables")
@pytest.mark.parametrize("tool", wasm_tools.TOOLS)
def test_macos_tools_need_only_system_libraries(tool: str) -> None:
    otool = shutil.which("otool")
    if otool is None:
        pytest.skip("no otool")
    out = subprocess.run(
        [otool, "-L", str(wasm_tools.get_executable(tool))], check=True, capture_output=True, text=True
    ).stdout
    # the libraries are the indented lines; a universal2 file has one unindented header per architecture
    libs = [line.split()[0] for line in out.splitlines() if line[:1].isspace()]
    bad = [lib for lib in libs if not _MACOS_OK.match(lib)]
    assert not bad, f"{tool} needs {bad} (all: {libs})"


@pytest.mark.skipif(sys.platform != "win32", reason="PE executables")
@pytest.mark.parametrize("tool", wasm_tools.TOOLS)
def test_windows_tools_do_not_import_the_c_runtime_dlls(tool: str) -> None:
    data = wasm_tools.get_executable(tool).read_bytes()
    found = [name.decode() for name in _WINDOWS_BAD if name.lower() in data.lower()]
    assert not found, f"{tool} refers to {found}: the C runtime must be linked in (+crt-static)"


@pytest.mark.skipif(sys.platform != "darwin", reason="Mach-O executables")
@pytest.mark.parametrize("tool", wasm_tools.TOOLS)
def test_macos_tools_do_not_need_a_newer_macos_than_the_wheel_says(tool: str) -> None:
    """MACOSX_DEPLOYMENT_TARGET is 11.0 (pyproject.toml): a tool that asks for a newer system would not start on an older one."""
    if not os.environ.get("CIBUILDWHEEL"):
        pytest.skip("not a cibuildwheel build: MACOSX_DEPLOYMENT_TARGET is not set, the SDK's default applies")
    otool = shutil.which("otool")
    if otool is None:
        pytest.skip("no otool")
    out = subprocess.run(
        [otool, "-l", str(wasm_tools.get_executable(tool))], check=True, capture_output=True, text=True
    ).stdout
    # LC_BUILD_VERSION says `minos`; its `tool ... version` lines are the linker's own version, not a system's
    found: list[tuple[str, str]] = []
    for block in out.split("Load command ")[1:]:
        if "cmd LC_BUILD_VERSION" in block:
            found += re.findall(r"^\s*minos\s+(\d+)\.(\d+)", block, flags=re.MULTILINE)
        elif "cmd LC_VERSION_MIN_" in block:
            found += re.findall(r"^\s*version\s+(\d+)\.(\d+)", block, flags=re.MULTILINE)
    if not found:
        pytest.skip("no minimum system version in the load commands")
    newest = max((int(a), int(b)) for a, b in found)
    assert newest <= (11, 0), f"{tool} needs macOS {newest[0]}.{newest[1]}"
