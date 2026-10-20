# Third-party material

This package redistributes, unmodified, the `wasm-tools` command-line executable of
[wasm-tools](https://github.com/bytecodealliance/wasm-tools) (the Bytecode Alliance), built from the release tag recorded in
`_wasm_tools_version.txt`. It is **not an official wasm-tools release** and is not affiliated with the Bytecode Alliance.

- wasm-tools: Copyright the Wasmtime Project Developers. Licence: Apache-2.0 WITH LLVM-exception, Apache-2.0 or MIT, at your
  option. The texts are `wasm-tools/LICENSE-Apache-2.0_WITH_LLVM-exception`, `wasm-tools/LICENSE-APACHE` and
  `wasm-tools/LICENSE-MIT` (in the sdist) / `licenses/wasm-tools/` (in the wheel's metadata).
- The executable is statically linked with the Rust crates that wasm-tools depends on, exactly the ones pinned in the
  `Cargo.lock` of that release (`wasm-tools/Cargo.lock`, in the sdist). They are open-source crates from
  [crates.io](https://crates.io) under their own licences (mostly MIT and Apache-2.0); see each crate's metadata.

The packaging code of this repository (`build_wasm_tools.py`, `setup.py`, `src/wasm_tools_package/`) is licensed under the
Apache License 2.0 (see `LICENSE`).
