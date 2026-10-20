# wasm-tools-package

[![license]][license-url]
[![pypi version]][PyPiUrl]
[![python versions]][PyPiUrl]
[![Pre-commit]][pre-commit-workflow]
[![coverage]][CodecovUrl]

[wasm-tools](https://github.com/bytecodealliance/wasm-tools), the Bytecode Alliance's WebAssembly toolkit, as a Python
package: the prebuilt `wasm-tools` executable, installable with `pip`. Like `libusb-package`, but for wasm-tools.
An unofficial redistribution (Apache-2.0 WITH LLVM-exception, Apache-2.0 or MIT).

```sh
pip install wasm-tools-package
wasm-tools parse add.wat -o add.wasm
wasm-tools validate add.wasm
```

## Version

`x.y.z.b`: `x.y.z` is the wasm-tools release the executable is built from, `b` is the build number of this package
(`1.262.0.0` is wasm-tools 1.262.0, first build). Requires Python 3.11+.

## What is in it

|            |                                                                                                                                                      |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| executable | `wasm-tools`, with all its subcommands: `parse`, `print`, `validate`, `component`, `objdump`, `dump`, `strip`, `smith`, `shrink`, `mutate`, `wast`, ... |

It is a console script; `python -m wasm_tools_package parse ...` runs it without relying on `PATH`.

```python
import wasm_tools_package as wasm_tools

wasm_tools.run("parse", "in.wat", "-o", "out.wasm")  # subprocess.run, check=True by default
wasm_tools.get_executable()  # pathlib.Path
wasm_tools.wasm_tools_version()  # "1.262.0"
```

## Wheels

The publish workflow builds `py3-none-<platform>` wheels (the executable does not depend on the interpreter) for the desktop platforms
of [cibuildwheel](https://cibuildwheel.pypa.io):

|                  |                               |
| ---------------- | ----------------------------- |
| Linux, manylinux | x86_64, aarch64, i686, armv7l |
| Linux, musllinux | x86_64, aarch64               |
| Windows          | x64, ARM64, x86               |
| macOS            | arm64, x86_64, universal2     |

See [CHANGELOG.md](CHANGELOG.md) for what each release has. There are no wheels for Android, iOS or
Pyodide: the tool runs on the machine that builds, and a package for those targets is built with the wheel of the host.
Anywhere else the sdist builds the executable from source and needs Rust 1.88 or newer (`cargo`, e.g. from [rustup](https://rustup.rs))
and network access to crates.io.

The Windows executable has the C runtime linked in, the Linux and macOS ones need only the system's own libraries (a test checks it on every platform).

## Development

```sh
git clone --recurse-submodules https://github.com/natify-sh/wasm-tools-package
cd wasm-tools-package
uv sync          # builds wasm-tools (a few minutes, needs cargo) and installs the package in editable mode
uv run pytest
```

`--recurse-submodules` also fetches the spec test suites of wasm-tools, which the build does not need; `git submodule update --init wasm-tools` is enough.

To move to a new wasm-tools release: check out its tag in `wasm-tools/`, commit the submodule, and tag `v<release>.0`
(the publish workflow checks that the tag starts with the submodule's release).

## License

Apache-2.0 for the packaging; wasm-tools itself is Apache-2.0 WITH LLVM-exception, Apache-2.0 or MIT. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).



<!-- REUSABLE LINKS -->

[license]:
https://img.shields.io/github/license/natify-sh/wasm-tools-package

[license-url]:
https://opensource.org/licenses/Apache-2.0

[pypi version]:
https://img.shields.io/pypi/v/wasm-tools-package?logo=pypi

[python versions]:
https://img.shields.io/pypi/pyversions/wasm-tools-package?logo=python

[PyPiUrl]:
https://pypi.org/project/wasm-tools-package/

[Pre-commit]:
https://github.com/natify-sh/wasm-tools-package/actions/workflows/pre-commit.yml/badge.svg

[pre-commit-workflow]:
https://github.com/natify-sh/wasm-tools-package/actions/workflows/pre-commit.yml

[coverage]:
https://codecov.io/gh/natify-sh/wasm-tools-package/graph/badge.svg

[CodecovUrl]:
https://codecov.io/gh/natify-sh/wasm-tools-package
