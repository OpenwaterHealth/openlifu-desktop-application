#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterable


SUCCESS = 0
HARD_FAILURE = 1
CYCLONEDX_FAILURE = 2
READY_MARKER = ".openlifu-environment-tools-ready"

CYCLONEDX_BOOTSTRAP = (
    "import runpy, sys; "
    "tool_dir = sys.argv.pop(1); "
    "sys.path.insert(0, tool_dir); "
    "runpy.run_module('cyclonedx_py', run_name='__main__', alter_sys=True)"
)


class GenerationError(RuntimeError):
    pass


def normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def run_command(command: list[str]) -> str:
    environment = os.environ.copy()
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    environment["PIP_NO_INPUT"] = "1"
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        shell=False,
    )
    if result.returncode != 0:
        details = "\n".join(
            output.strip()
            for output in (result.stdout, result.stderr)
            if output.strip()
        )
        raise GenerationError(
            f"command failed with exit code {result.returncode}: "
            f"{command[0]} {' '.join(command[1:])}\n{details}"
        )
    return result.stdout


def parse_pip_inventory(output: str) -> dict[str, tuple[str, str]]:
    packages: dict[str, tuple[str, str]] = {}
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if "==" not in line:
            raise GenerationError(f"unexpected pip inventory line: {line!r}")
        name, version = line.split("==", 1)
        if not name or not version:
            raise GenerationError(f"incomplete pip inventory line: {line!r}")
        key = normalized_name(name)
        if key in packages:
            raise GenerationError(f"duplicate normalized package name: {name}")
        packages[key] = (name, version)
    if not packages:
        raise GenerationError("pip returned an empty package inventory")
    return packages


def render_pip_inventory(packages: dict[str, tuple[str, str]]) -> str:
    return "".join(
        f"{name}=={version}\n"
        for _, (name, version) in sorted(packages.items())
    )


def atomic_write_text(path: Path, content: str, temporary_directory: Path) -> None:
    temporary_path = temporary_directory / path.name
    temporary_path.write_text(content, encoding="utf-8", newline="\n")
    os.replace(temporary_path, path)


def component_map(document: dict[str, Any]) -> dict[str, tuple[str, str]]:
    if document.get("bomFormat") != "CycloneDX":
        raise GenerationError("CycloneDX output has an unexpected bomFormat")
    if document.get("specVersion") != "1.6":
        raise GenerationError("CycloneDX output is not specification version 1.6")
    components = document.get("components")
    if not isinstance(components, list):
        raise GenerationError("CycloneDX output has no top-level components list")

    packages: dict[str, tuple[str, str]] = {}
    for component in components:
        if not isinstance(component, dict):
            raise GenerationError("CycloneDX output contains an invalid component")
        name = component.get("name")
        version = component.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            raise GenerationError("CycloneDX component is missing a name or version")
        key = normalized_name(name)
        if key in packages:
            raise GenerationError(f"duplicate CycloneDX component name: {name}")
        packages[key] = (name, version)
    return packages


def validate_component_parity(
    pip_packages: dict[str, tuple[str, str]],
    cyclonedx_packages: dict[str, tuple[str, str]],
) -> None:
    pip_keys = set(pip_packages)
    cyclonedx_keys = set(cyclonedx_packages)
    problems: list[str] = []
    if missing := sorted(pip_keys - cyclonedx_keys):
        problems.append(f"missing components: {', '.join(missing[:8])}")
    if extra := sorted(cyclonedx_keys - pip_keys):
        problems.append(f"unexpected components: {', '.join(extra[:8])}")
    mismatches = sorted(
        key
        for key in pip_keys & cyclonedx_keys
        if pip_packages[key][1] != cyclonedx_packages[key][1]
    )
    if mismatches:
        problems.append(f"version mismatches: {', '.join(mismatches[:8])}")
    if problems:
        raise GenerationError("CycloneDX/pip inventory mismatch; " + "; ".join(problems))


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_strings(child)


def is_local_file_reference(value: str) -> bool:
    folded = value.casefold()
    return folded.startswith("file:") or "file%3a" in folded


def remove_local_external_references(value: Any) -> None:
    if isinstance(value, dict):
        external_references = value.get("externalReferences")
        if isinstance(external_references, list):
            retained_references = [
                reference
                for reference in external_references
                if not (
                    isinstance(reference, dict)
                    and isinstance(reference.get("url"), str)
                    and is_local_file_reference(reference["url"])
                )
            ]
            if retained_references:
                value["externalReferences"] = retained_references
            else:
                del value["externalReferences"]
        for child in value.values():
            remove_local_external_references(child)
    elif isinstance(value, list):
        for child in value:
            remove_local_external_references(child)


def validate_no_sensitive_references(
    document: dict[str, Any], forbidden_paths: list[str]
) -> None:
    path_variants: list[str] = []
    for path in forbidden_paths:
        if not path:
            continue
        absolute_path = str(Path(path).resolve())
        anchor = Path(absolute_path).anchor
        if absolute_path == anchor:
            continue
        path_variants.extend(
            [absolute_path.casefold(), absolute_path.replace("\\", "/").casefold()]
        )

    credential_url = re.compile(r"https?://[^/\s]+@", re.IGNORECASE)
    for value in iter_strings(document):
        folded = value.casefold()
        forward_slash_value = value.replace("\\", "/").casefold()
        if any(
            variant in folded or variant in forward_slash_value
            for variant in path_variants
        ):
            raise GenerationError("CycloneDX output contains a build or source path")
        if is_local_file_reference(value):
            raise GenerationError("CycloneDX output contains a local file reference")
        if credential_url.search(value):
            raise GenerationError("CycloneDX output contains a credential-bearing URL")


def generate_cyclonedx(
    target_python: str,
    tool_directory: Path,
    expected_tool_lock_hash: str,
    temporary_path: Path,
) -> dict[str, Any]:
    ready_marker = tool_directory / READY_MARKER
    if not ready_marker.is_file():
        raise GenerationError("CycloneDX environment tools are not available")
    try:
        installed_tool_lock_hash = ready_marker.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise GenerationError(f"could not read the CycloneDX tool marker: {error}") from error
    if installed_tool_lock_hash != expected_tool_lock_hash:
        raise GenerationError("CycloneDX environment tools do not match the lock file")

    run_command(
        [
            target_python,
            "-I",
            "-c",
            CYCLONEDX_BOOTSTRAP,
            str(tool_directory),
            "environment",
            "--spec-version",
            "1.6",
            "--output-format",
            "JSON",
            "--output-reproducible",
            "--validate",
            "--output-file",
            str(temporary_path),
            target_python,
        ]
    )
    try:
        document = json.loads(temporary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GenerationError(f"could not read CycloneDX output: {error}") from error
    if not isinstance(document, dict):
        raise GenerationError("CycloneDX output is not a JSON object")
    return document


def common_build_root(target_python: str, tool_directory: Path) -> str | None:
    try:
        common_path = Path(os.path.commonpath([target_python, str(tool_directory)]))
    except ValueError:
        return None
    if str(common_path) == common_path.anchor:
        return None
    return str(common_path)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-python", required=True)
    parser.add_argument("--tool-dir", required=True)
    parser.add_argument("--tool-lock-hash", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--forbidden-path", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    target_python = str(Path(arguments.target_python).resolve())
    tool_directory = Path(arguments.tool_dir).resolve()
    output_directory = Path(arguments.output_dir).resolve()
    text_path = output_directory / "python-environment.txt"
    cyclonedx_path = output_directory / "python-environment.cdx.json"

    output_directory.mkdir(parents=True, exist_ok=True)
    text_path.unlink(missing_ok=True)
    cyclonedx_path.unlink(missing_ok=True)

    try:
        run_command([target_python, "-m", "pip", "check"])
        pip_output = run_command(
            [target_python, "-m", "pip", "list", "--format=freeze"]
        )
        pip_packages = parse_pip_inventory(pip_output)
        with tempfile.TemporaryDirectory(
            prefix=".python-environment-", dir=output_directory
        ) as temporary_directory_name:
            temporary_directory = Path(temporary_directory_name)
            atomic_write_text(
                text_path,
                render_pip_inventory(pip_packages),
                temporary_directory,
            )

            try:
                temporary_cyclonedx_path = temporary_directory / cyclonedx_path.name
                document = generate_cyclonedx(
                    target_python,
                    tool_directory,
                    arguments.tool_lock_hash,
                    temporary_cyclonedx_path,
                )
                validate_component_parity(pip_packages, component_map(document))
                remove_local_external_references(document)
                forbidden_paths = list(arguments.forbidden_path)
                forbidden_paths.extend([str(tool_directory), target_python])
                if root := common_build_root(target_python, tool_directory):
                    forbidden_paths.append(root)
                validate_no_sensitive_references(document, forbidden_paths)
                temporary_cyclonedx_path.write_text(
                    json.dumps(document, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                os.replace(temporary_cyclonedx_path, cyclonedx_path)
            except (GenerationError, OSError) as error:
                cyclonedx_path.unlink(missing_ok=True)
                print(
                    f"warning: CycloneDX environment artifact was omitted: {error}",
                    file=sys.stderr,
                )
                return CYCLONEDX_FAILURE
    except (GenerationError, OSError) as error:
        text_path.unlink(missing_ok=True)
        cyclonedx_path.unlink(missing_ok=True)
        print(
            f"error: could not generate the pip environment artifact: {error}",
            file=sys.stderr,
        )
        return HARD_FAILURE

    return SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
