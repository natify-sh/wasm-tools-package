"""Build the `wasm-tools` executable from the `wasm-tools` submodule and stage it inside the package.

    src/wasm_tools_package/bin/wasm-tools[.exe]             the executable (wasm_tools_package.TOOLS)
    src/wasm_tools_package/_wasm_tools_version.txt          the wasm-tools version, from the submodule's tag

Runs from setup.py on every build (wheel, sdist -> wheel, editable `uv sync`), and by hand as
`uv run python build_wasm_tools.py`. Plain Python so it works on Windows too.

Sources: the `wasm-tools` git submodule, pinned to a release tag (shipped inside the sdist). It is built with the platform's own
Rust toolchain (`cargo`, from rustup or the system), `--locked` to the Cargo.lock of the release; the crates it depends on come
from crates.io. Unlike WABT, all of wasm-tools is Rust, so there is no C++ runtime to link in; the Windows build links the C
runtime statically, and a macOS universal2 build is two cargo builds joined with `lipo`.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WASM_TOOLS_DIR = Path(os.environ.get("WASM_TOOLS_DIR") or ROOT / "wasm-tools")
OUT_DIR = ROOT / "src" / "wasm_tools_package"
# One build tree per target: cibuildwheel builds several architectures one after the other on a runner (Windows x86 and
# x64, macOS arm64 and universal2), and they must not overwrite each other's work.
_TARGET = "-".join(
    part
    for part in (sysconfig.get_platform(), *(os.environ.get("ARCHFLAGS", "").replace("-arch", " ").split()))
    if part
)
BUILD_DIR = ROOT / "build" / f"wasm-tools-{_TARGET}"
# Written into the sdist (see setup.py), where the submodule's git metadata is not available.
VERSION_FILE = OUT_DIR / "_wasm_tools_version.txt"
STAMP_FILE = BUILD_DIR / "staged.stamp"

# Keep in sync with wasm_tools_package.TOOLS and [project.scripts]. wasm-tools is a single executable with subcommands.
TOOLS = ("wasm-tools",)
EXE_SUFFIX = ".exe" if sys.platform == "win32" else ""

_DARWIN_TARGETS = {"arm64": "aarch64-apple-darwin", "x86_64": "x86_64-apple-darwin"}
_WINDOWS_TARGETS = {
    "win-amd64": "x86_64-pc-windows-msvc",
    "win-arm64": "aarch64-pc-windows-msvc",
    "win32": "i686-pc-windows-msvc",
}


def wasm_tools_version() -> str:
    """`git describe` of the submodule (release tags `v<version>` only), else the version recorded in the sdist, else "unknown"."""
    try:
        out = subprocess.run(
            ["git", "-C", str(WASM_TOOLS_DIR), "describe", "--tags", "--always", "--match", "v[0-9]*"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if out:
            return out.removeprefix("v")
    except (OSError, subprocess.CalledProcessError):
        pass
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    return "unknown"


def _run(cmd: list[str], env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)


def _cargo() -> str:
    found = shutil.which("cargo") or shutil.which("cargo", path=str(Path.home() / ".cargo" / "bin"))
    if not found:
        raise SystemExit(
            "cargo was not found: install a Rust toolchain (https://rustup.rs, Rust 1.88 or newer). It is the build "
            "requirement of the sdist; the wheels carry the executable already."
        )
    return found


def _targets() -> list[str | None]:
    """The Rust targets to build: None is the host's own (Linux, and any build for the interpreter's own architecture)."""
    if sys.platform == "win32":
        triple = _WINDOWS_TARGETS.get(sysconfig.get_platform())
        return [triple] if triple else [None]
    if sys.platform == "darwin":
        archs = [a for a in os.environ.get("ARCHFLAGS", "").replace("-arch", " ").split() if a]
        triples = [_DARWIN_TARGETS[a] for a in archs if a in _DARWIN_TARGETS]
        return list(dict.fromkeys(triples)) or [None]
    return [None]


def _build_env() -> dict[str, str]:
    """The environment of `cargo`: stripped release binary; on Windows the C runtime linked in (no vcruntime DLL needed at the
    user's)."""
    env = dict(os.environ)
    env.setdefault("CARGO_PROFILE_RELEASE_STRIP", "symbols")
    if sys.platform == "win32":
        env["RUSTFLAGS"] = f"{env.get('RUSTFLAGS', '')} -C target-feature=+crt-static".strip()
    return env


def _locate(target: str | None) -> Path:
    path = BUILD_DIR / (target or "") / "release" / ("wasm-tools" + EXE_SUFFIX)
    if not path.exists():
        raise SystemExit(f"wasm-tools was not built: not found at {path}")
    return path


def _stamp(version: str) -> str:
    # What the staged file depends on: the wasm-tools version, this script, the platform and the compiler settings in play.
    parts = [
        version,
        sysconfig.get_platform(),
        os.environ.get("ARCHFLAGS", ""),
        os.environ.get("MACOSX_DEPLOYMENT_TARGET", ""),
        os.environ.get("RUSTFLAGS", ""),
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    ]
    return "\n".join(parts)


def _staged(stamp: str) -> bool:
    if not (STAMP_FILE.exists() and STAMP_FILE.read_text(encoding="utf-8") == stamp):
        return False
    return all((OUT_DIR / "bin" / (t + EXE_SUFFIX)).exists() for t in TOOLS)


def build() -> None:
    if not WASM_TOOLS_DIR.joinpath("Cargo.toml").exists():
        raise SystemExit(f"{WASM_TOOLS_DIR} has no Cargo.toml: run `git submodule update --init wasm-tools`")
    version = wasm_tools_version()
    stamp = _stamp(version)
    if _staged(stamp):
        print(f"wasm-tools {version} is already staged in {OUT_DIR}")
        return
    cargo = _cargo()
    env = _build_env()
    rustup = shutil.which("rustup")

    built: list[Path] = []
    for target in _targets():
        if target and rustup:  # a cross target (universal2, Windows x86) may not be installed yet; harmless if it is
            subprocess.run([rustup, "target", "add", target], check=False)
        cmd = [
            cargo,
            "build",
            "--release",
            "--locked",
            "--bin",
            "wasm-tools",
            "--manifest-path",
            str(WASM_TOOLS_DIR / "Cargo.toml"),
            "--target-dir",
            str(BUILD_DIR),
        ]
        if target:
            cmd += ["--target", target]
        _run(cmd, env)
        built.append(_locate(target))

    bin_dir = OUT_DIR / "bin"
    shutil.rmtree(bin_dir, ignore_errors=True)
    bin_dir.mkdir(parents=True)
    staged = bin_dir / ("wasm-tools" + EXE_SUFFIX)
    if len(built) == 1:
        shutil.copy2(built[0], staged)
    else:  # macOS universal2
        _run(["lipo", "-create", *map(str, built), "-output", str(staged)])
    VERSION_FILE.write_text(version + "\n", encoding="utf-8")
    STAMP_FILE.parent.mkdir(parents=True, exist_ok=True)
    STAMP_FILE.write_text(stamp, encoding="utf-8")
    print(f"staged wasm-tools {version} in {OUT_DIR}")


if __name__ == "__main__":
    build()
