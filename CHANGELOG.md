# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The version is the wasm-tools release the
executable is built from plus a build number: `1.262.0.0` is wasm-tools 1.262.0, first build.

## [Unreleased]

### Added
- wasm-tools 1.262.0 built from the `wasm-tools` submodule, pinned to its release tag. The `wasm-tools` executable (all its
  subcommands: `parse`, `print`, `validate`, `component`, `objdump`, `strip`, `smith`, `wast`, ...) is a console script, and
  `python -m wasm_tools_package ...` runs it without relying on `PATH`.
- Python API: `run()` (`subprocess.run`, `check=True` by default), `get_executable()`, `bin_dir()`, `TOOLS`,
  `wasm_tools_version()`. The package is typed (`py.typed`) and has no dependencies; Python 3.11+, CPython and PyPy.
- `py3-none-<platform>` wheels built with cibuildwheel (the executable does not depend on the interpreter):
  - Linux: manylinux x86_64, aarch64, i686, armv7l; musllinux x86_64, aarch64
  - Windows: x64, ARM64, x86 (the C runtime linked in)
  - macOS: arm64, x86_64, universal2 (minimum macOS 11.0)
- An sdist that builds the executable from source with Rust 1.88 or newer (the crates come from crates.io, pinned by the
  release's `Cargo.lock`), for every platform without a wheel.
- The version is derived from the git tag (`v1.262.0.0` is wasm-tools 1.262.0, build 0) with setuptools-scm; the publish
  workflow checks that the tag starts with the release of the `wasm-tools` submodule.
- Publish workflow: a tag push publishes to PyPI (trusted publishing) and creates a GitHub Release with the section of this
  file; a manual run can publish to TestPyPI with an overridden version; pull requests build everything without publishing.

### Tests
- The executable runs; `.wat` -> `.wasm` -> `.wat` round trip; a core module becomes a component (`component embed`/`new`).
- Every wheel is checked on its platform to depend on nothing but the system (Linux: the C library and libgcc_s; macOS: only
  system libraries and no newer macOS than the wheel says; Windows: no C runtime DLLs).

[Unreleased]: https://github.com/natify-sh/wasm-tools-package/commits/main
