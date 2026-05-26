# Repository Guidelines

## Project Structure & Module Organization

OpenLIFU-app is a CMake custom 3D Slicer application. `CMakeLists.txt` pins Slicer and extension `GIT_TAG`s. App C++ and Qt resources live in `Applications/OpenLIFUApp/`. The local app shell module is `Modules/Scripted/Home/`; most workflow modules are bundled from [SlicerOpenLIFU](https://github.com/OpenwaterHealth/SlicerOpenLIFU). Core algorithms, database models, beamforming, simulation, hardware I/O, and photoscan support live in [OpenLIFU-python](https://github.com/OpenwaterHealth/OpenLIFU-python). Make behavioral changes in the owning repo, then update the app pin or requirements.

## Build, Test, and Development Commands

Use an out-of-source superbuild directory. Set `Qt5_DIR` to the local Qt 5.15.2 CMake package:

```sh
mkdir OpenLIFU-superbuild
cmake -DCMAKE_BUILD_TYPE:STRING=Release \
  -DQt5_DIR:PATH=/path/to/Qt/5.15.2/gcc_64/lib/cmake/Qt5 \
  -S OpenLIFU-app -B OpenLIFU-superbuild
cmake --build OpenLIFU-superbuild --parallel
```

The inner Slicer build is `OpenLIFU-superbuild/Slicer-build`. Package there with `cmake --build . --target package` or `make package`. Windows builds use `cmake --build . --config Release`; see `BUILD_WINDOWS.md`. For platform details, use the [Slicer build instructions](https://slicer.readthedocs.io/en/latest/developer_guide/build_instructions/index.html) and [extension guide](https://slicer.readthedocs.io/en/latest/developer_guide/extensions.html).

## Coding Style & Naming Conventions

Follow local Slicer style first. C++ classes use Qt/Slicer names such as `qOpenLIFUAppMainWindow`; pair `.h` and `.cxx` files. Python scripted modules use 4-space indentation and Slicer patterns: `<Module>`, `<Module>Widget`, `<Module>Logic`, `<Module>Test`. Keep `.ui` files in `Resources/UI/`, icons in `Resources/Icons/`, and update `.qrc` manifests with assets. CMake uses 2-space indentation, lowercase commands, and uppercase globals. OpenLIFU-python uses Ruff, pre-commit, PyLint via `nox`, and requires `from __future__ import annotations`.

## Testing Guidelines

`BUILD_TESTING` defaults to `OFF`. Enabling it requires `-DBUILD_TESTING:BOOL=ON` and a valid `-DDVC_GDRIVE_KEY_PATH:FILEPATH=/path/to/key.json`, because `SlicerOpenLIFU` downloads integration-test data with DVC. Run tests from the inner build:

```sh
ctest --test-dir OpenLIFU-superbuild/Slicer-build --output-on-failure
```

`SlicerOpenLIFU` tests run inside Slicer with CTest and `ScriptedLoadableModuleTest`; names follow `py_<ModuleName>`, and `py_OpenLIFUHome` drives the full workflow. For core library changes in OpenLIFU-python, run `pytest`, `nox -s lint`, and `nox -s pylint` in that repository.

## Commit & Pull Request Guidelines

Each commit should be granular and reference a GitHub issue, for example `Fix login startup race (#123)`. CI allows issue refs, full issue URLs, and prefixes such as `Bump`, `Merge`, `Revert`, `fixup!`, `squash!`, and `amend!`. Do not squash PRs on merge. PRs should describe behavior changes, link issues, include screenshots for UI changes, and note build/test results.

## Security & Configuration Tips

Do not commit service account keys, DVC credentials, downloaded assets, sample databases, or superbuild outputs. Keep generated directories such as `OpenLIFU-superbuild/`, `Slicer-build/`, and dependency source/build folders outside commits. Meshroom is needed on `PATH` only for local photogrammetry reconstruction.
