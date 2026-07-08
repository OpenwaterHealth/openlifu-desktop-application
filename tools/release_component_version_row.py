#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Generate one OpenLIFU release component version table row."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

WORKTREE_REF = "WORKTREE"
APP_PROPERTIES_PATH = "Applications/OpenLIFUApp/slicer-application-properties.cmake"
SLICEROPENLIFU_REQUIREMENTS_PATH = (
    "OpenLIFULib/OpenLIFULib/Resources/python-requirements.txt"
)
SLICEROPENLIFU_SAMPLE_DATA_PATH = "OpenLIFULib/OpenLIFULib/sample_data.py"
SLICER_REPOSITORY_URL = "https://github.com/Slicer/Slicer.git"


class RowError(RuntimeError):
    pass


def run_git(repo: Path, *args: str) -> str:
    command = ["git", "-C", str(repo), *args]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RowError(f"git command failed: {' '.join(command)}\n{detail}")
    return result.stdout


def read_repo_file(repo: Path, ref: str, path: str) -> str:
    if ref == WORKTREE_REF:
        file_path = repo / path
        try:
            return file_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise RowError(f"file not found: {file_path}") from exc

    try:
        return run_git(repo, "show", f"{ref}:{path}")
    except RowError as exc:
        raise RowError(f"could not read {path!r} at {ref!r} in {repo}") from exc


def first_cmake_value(text: str, variable_name: str) -> str:
    pattern = rf"set\s*\(\s*{re.escape(variable_name)}\s+(?P<body>.*?)\)"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        raise RowError(f"could not find CMake variable {variable_name}")
    body = re.sub(r"#.*", "", match.group("body"))
    tokens = [token.strip('"') for token in body.split() if token.strip()]
    if not tokens:
        raise RowError(f"CMake variable {variable_name} has no value")
    return tokens[0]


def fetchcontent_git_tag(text: str, block_name: str) -> str:
    pattern = rf"FetchContent_Populate\s*\(\s*{re.escape(block_name)}(?P<body>.*?)\n\s*\)"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        raise RowError(f"could not find FetchContent_Populate({block_name})")
    return git_tag_from_block(match.group("body"), block_name)


def sliceropenlifu_git_tag(text: str) -> str:
    marker = 'set(extension_name "SlicerOpenLIFU")'
    start = text.find(marker)
    if start == -1:
        raise RowError('could not find set(extension_name "SlicerOpenLIFU")')
    return git_tag_from_block(text[start:], "SlicerOpenLIFU")


def git_tag_from_block(text: str, label: str) -> str:
    match = re.search(r"\bGIT_TAG\s+(?P<tag>[^\s)#]+)", text)
    if not match:
        raise RowError(f"could not find GIT_TAG for {label}")
    return match.group("tag").strip('"')


def app_version(app_repo: Path, app_ref: str, override: str | None) -> str:
    if override:
        return override
    if app_ref != WORKTREE_REF and app_ref.startswith("v"):
        return app_ref

    properties = read_repo_file(app_repo, app_ref, APP_PROPERTIES_PATH)
    major = first_cmake_value(properties, "VERSION_MAJOR")
    minor = first_cmake_value(properties, "VERSION_MINOR")
    patch = first_cmake_value(properties, "VERSION_PATCH")
    return f"v{major}.{minor}.{patch}"


def openlifu_pin(requirements_text: str) -> str:
    for raw_line in requirements_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("git+") and "openlifu-python" in line:
            tag_match = re.search(r"@(?P<tag>[^#\s]+)", line)
            if tag_match:
                return normalize_version(tag_match.group("tag"))

        pin_match = re.match(r"openlifu(?:\[[^\]]+\])?\s*==\s*(?P<pin>\S+)", line)
        if pin_match:
            return normalize_version(pin_match.group("pin"))

    raise RowError("could not find an openlifu pin in python-requirements.txt")


def normalize_version(version: str) -> str:
    cleaned = version.strip()
    if cleaned.startswith("v"):
        return cleaned
    if re.match(r"^\d+\.\d+\.\d+(?:[-+].*)?$", cleaned):
        return f"v{cleaned}"
    return cleaned


def sample_database_from_sliceropenlifu(
    sliceropenlifu_repo: Path,
    sliceropenlifu_ref: str,
) -> str | None:
    try:
        sample_data = read_repo_file(
            sliceropenlifu_repo,
            sliceropenlifu_ref,
            SLICEROPENLIFU_SAMPLE_DATA_PATH,
        )
    except RowError:
        return None

    match = re.search(
        r'^SAMPLE_DATABASE_TAG\s*=\s*["\'](?P<tag>[^"\']+)["\']',
        sample_data,
        flags=re.MULTILINE,
    )
    if not match:
        return None
    return f"openlifu-sample-database: {match.group('tag')}"


def sample_database_from_openlifu_readme(openlifu_repo: Path, openlifu_ref: str) -> str | None:
    for readme_path in ("README.md", "README.rst"):
        try:
            readme = read_repo_file(openlifu_repo, openlifu_ref, readme_path)
        except RowError:
            continue
        if "openlifu-sample-database" not in readme:
            continue
        match = re.search(
            r"--branch\s+(?P<tag>\S+)\s+https://github\.com/OpenwaterHealth/openlifu-sample-database",
            readme,
        )
        if match:
            return f"openlifu-sample-database: {match.group('tag')}"
    return None


def default_sibling_repo(app_repo: Path, *names: str) -> Path | None:
    for name in names:
        candidate = app_repo.parent / name
        if (candidate / ".git").exists():
            return candidate
    return None


def existing_repo(path: str | None, label: str) -> Path | None:
    if path is None:
        return None
    repo = Path(path).expanduser().resolve()
    if not (repo / ".git").exists():
        raise RowError(f"{label} is not a git repository: {repo}")
    return repo


def generate_row(args: argparse.Namespace) -> str:
    app_repo = existing_repo(args.app_repo, "app repo")
    if app_repo is None:
        app_repo = Path(__file__).resolve().parents[1]

    sliceropenlifu_repo = existing_repo(args.sliceropenlifu_repo, "SlicerOpenLIFU repo")
    if sliceropenlifu_repo is None:
        sliceropenlifu_repo = default_sibling_repo(app_repo, "SlicerOpenLIFU")
    if sliceropenlifu_repo is None:
        raise RowError("could not find SlicerOpenLIFU repo; pass --sliceropenlifu-repo")

    openlifu_repo = existing_repo(args.openlifu_repo, "OpenLIFU-python repo")
    if openlifu_repo is None:
        openlifu_repo = default_sibling_repo(app_repo, "OpenLIFU-python", "openlifu-python")

    cmake = read_repo_file(app_repo, args.app_ref, "CMakeLists.txt")
    slicer_ref = fetchcontent_git_tag(cmake, "slicersources")
    sliceropenlifu_ref = sliceropenlifu_git_tag(cmake)

    requirements = read_repo_file(
        sliceropenlifu_repo,
        sliceropenlifu_ref,
        SLICEROPENLIFU_REQUIREMENTS_PATH,
    )
    openlifu_ref = openlifu_pin(requirements)

    sample_database = args.sample_database
    if sample_database is None:
        sample_database = sample_database_from_sliceropenlifu(
            sliceropenlifu_repo,
            sliceropenlifu_ref,
        )
    if sample_database is None and openlifu_repo is not None:
        sample_database = sample_database_from_openlifu_readme(openlifu_repo, openlifu_ref)
    if sample_database is None:
        sample_database = "TODO: sample database"

    values = [
        app_version(app_repo, args.app_ref, args.app_version),
        short_ref(sliceropenlifu_ref),
        openlifu_ref,
        slicer_source_value(slicer_ref),
        sample_database,
    ]
    row = "| " + " | ".join(f"`{value}`" for value in values) + " |"

    if args.header:
        header = "| OpenLIFU app | SlicerOpenLIFU | `openlifu` Python package | 3D Slicer source | Sample database |"
        separator = "| --- | --- | --- | --- | --- |"
        return "\n".join((header, separator, row))
    return row


def short_ref(ref: str) -> str:
    if re.match(r"^[0-9a-f]{40}$", ref):
        return ref[:8]
    return ref


def slicer_source_value(ref: str) -> str:
    if not re.match(r"^[0-9a-f]{40}$", ref):
        return ref

    tag = slicer_tag_for_commit(ref)
    if tag:
        return tag
    return short_ref(ref)


def slicer_tag_for_commit(commit_sha: str) -> str | None:
    result = subprocess.run(
        ["git", "ls-remote", "--tags", SLICER_REPOSITORY_URL],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    matching_tags: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        sha, ref = parts
        if sha != commit_sha:
            continue
        tag_name = ref.removeprefix("refs/tags/").removesuffix("^{}")
        if re.match(r"^v\d+\.\d+\.", tag_name):
            matching_tags.append(tag_name)

    if not matching_tags:
        return None
    return sorted(matching_tags, key=slicer_tag_sort_key)[-1]


def slicer_tag_sort_key(tag_name: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", tag_name))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate one row for docs/release-component-version-table.md.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""Examples:
  uv run tools/release_component_version_row.py
  uv run tools/release_component_version_row.py --app-version v1.13.0-rc.1
  uv run /path/to/OpenLIFU-app/tools/release_component_version_row.py --app-ref v1.12.0
  uv run tools/release_component_version_row.py --sample-database "openlifu-sample-database: openlifu-v0.21.0"

By default, the script reads the app working tree at:
  {Path(__file__).resolve().parents[1]}

Use --app-ref to inspect a committed app tag or branch instead.
""",
    )
    parser.add_argument(
        "--app-ref",
        default=WORKTREE_REF,
        help=f"App git ref to inspect. Defaults to {WORKTREE_REF}, meaning the working tree.",
    )
    parser.add_argument(
        "--app-version",
        help="App version to print, useful for RC tags before they exist.",
    )
    parser.add_argument(
        "--app-repo",
        help="Path to OpenLIFU-app. Defaults to the repository containing this script.",
    )
    parser.add_argument(
        "--sliceropenlifu-repo",
        help="Path to SlicerOpenLIFU. Defaults to ../SlicerOpenLIFU next to OpenLIFU-app.",
    )
    parser.add_argument(
        "--openlifu-repo",
        help="Path to OpenLIFU-python. Defaults to ../OpenLIFU-python next to OpenLIFU-app, if present.",
    )
    parser.add_argument(
        "--sample-database",
        help="Sample database value to print when it cannot be inferred, or when overriding is clearer.",
    )
    parser.add_argument(
        "--header",
        action="store_true",
        help="Print the table header and separator before the row.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        print(generate_row(args))
    except RowError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
