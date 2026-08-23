#!/usr/bin/env python3
"""Build, install, import, test, and audit utility wheels in isolation."""

from __future__ import annotations

import argparse
import ast
import concurrent.futures
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPOSITORY_ROOT / "tools" / "package_matrix.json"
TOOLCHAIN_PATH = REPOSITORY_ROOT / "tools" / "toolchain.json"
FORBIDDEN_DISTRIBUTIONS = {
    "librsi",
    "patent-studio",
    "software-factory",
    "utils",
}
NAME_PATTERN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def load_matrix() -> dict[str, object]:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def normalize_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def requirement_distribution(value: str) -> str:
    match = NAME_PATTERN.match(value)
    if match is None:
        raise RuntimeError(f"invalid runtime requirement: {value!r}")
    return normalize_distribution(match.group(1))


def package_records(matrix: dict[str, object]) -> dict[str, dict[str, str]]:
    raw = matrix.get("packages")
    if not isinstance(raw, dict):
        raise RuntimeError("package matrix is missing packages")
    records: dict[str, dict[str, str]] = {}
    for distribution, details in raw.items():
        if not isinstance(distribution, str) or not isinstance(details, dict):
            raise RuntimeError("package matrix contains a malformed record")
        if not all(isinstance(details.get(field), str) for field in ("path", "import", "version")):
            raise RuntimeError(f"package matrix record is incomplete: {distribution}")
        records[normalize_distribution(distribution)] = {
            "path": details["path"],
            "import": details["import"],
            "version": details["version"],
        }
    return records


def declared_runtime_dependencies(package_root: Path) -> tuple[str, ...]:
    document = tomllib.loads((package_root / "pyproject.toml").read_text(encoding="utf-8"))
    project = document.get("project")
    if not isinstance(project, dict):
        raise RuntimeError(f"package project metadata is missing: {package_root}")
    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list) or not all(
        isinstance(item, str) for item in dependencies
    ):
        raise RuntimeError(f"runtime dependencies are malformed: {package_root}")
    return tuple(sorted(requirement_distribution(item) for item in dependencies))


def audit_dependency_edges(
    distribution: str,
    dependencies: tuple[str, ...],
    admitted: set[str],
) -> None:
    forbidden = sorted(set(dependencies) & FORBIDDEN_DISTRIBUTIONS)
    if forbidden:
        raise RuntimeError(
            f"reverse/downstream dependency in {distribution}: {', '.join(forbidden)}"
        )
    unadmitted = sorted(set(dependencies) - admitted)
    if unadmitted:
        raise RuntimeError(
            f"unadmitted runtime dependency in {distribution}: {', '.join(unadmitted)}"
        )


def validate_acyclic_graph(graph: dict[str, tuple[str, ...]]) -> None:
    visited: set[str] = set()
    active: list[str] = []

    def visit(distribution: str) -> None:
        if distribution in active:
            start = active.index(distribution)
            cycle = [*active[start:], distribution]
            raise RuntimeError(f"circular package dependency: {' -> '.join(cycle)}")
        if distribution in visited:
            return
        active.append(distribution)
        for dependency in graph[distribution]:
            visit(dependency)
        active.pop()
        visited.add(distribution)

    for distribution in sorted(graph):
        visit(distribution)


def audit_dependency_graph(
    packages: dict[str, dict[str, str]],
) -> dict[str, tuple[str, ...]]:
    admitted = set(packages)
    graph: dict[str, tuple[str, ...]] = {}
    for distribution, package in packages.items():
        package_root = (REPOSITORY_ROOT / package["path"]).resolve()
        dependencies = declared_runtime_dependencies(package_root)
        audit_dependency_edges(distribution, dependencies, admitted)
        graph[distribution] = dependencies
    validate_acyclic_graph(graph)
    return graph


def require_uv() -> str:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required for the maintained package smoke envelope")
    toolchain = json.loads(TOOLCHAIN_PATH.read_text(encoding="utf-8"))
    actual = run([uv, "--version"], cwd=REPOSITORY_ROOT).stdout.strip()
    fields = actual.split(maxsplit=2)
    expected = str(toolchain["uv"])
    if len(fields) < 2 or fields[0] != "uv" or fields[1] != expected:
        raise RuntimeError(
            f"uv version mismatch: expected semantic version {expected!r}, got {actual!r}"
        )
    return uv


def environment_python(environment: Path) -> Path:
    posix = environment / "bin" / "python"
    return posix if posix.exists() else environment / "Scripts" / "python.exe"


def copy_package_snapshot(package_root: Path, destination: Path) -> None:
    symlinks = sorted(path for path in package_root.rglob("*") if path.is_symlink())
    if symlinks:
        relative = ", ".join(str(path.relative_to(package_root)) for path in symlinks)
        raise RuntimeError(f"package snapshot contains symlink(s): {relative}")
    shutil.copytree(
        package_root,
        destination,
        ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache", "build", "dist"
        ),
    )


def wheel_metadata(archive: zipfile.ZipFile) -> tuple[str, str, str, tuple[str, ...]]:
    names = [
        name
        for name in archive.namelist()
        if name.endswith(".dist-info/METADATA") and not name.endswith("/")
    ]
    if len(names) != 1:
        raise RuntimeError(f"wheel must contain exactly one METADATA file, found {len(names)}")
    message = BytesParser().parsebytes(archive.read(names[0]))
    name = message.get("Name")
    version = message.get("Version")
    requires_python = message.get("Requires-Python")
    if not all(isinstance(value, str) and value for value in (name, version, requires_python)):
        raise RuntimeError("wheel METADATA is missing Name, Version, or Requires-Python")
    dependencies = tuple(
        sorted(requirement_distribution(value) for value in message.get_all("Requires-Dist", []))
    )
    return normalize_distribution(name), version, requires_python, dependencies


def imported_roots_from_wheel(archive: zipfile.ZipFile) -> set[str]:
    roots: set[str] = set()
    for name in sorted(archive.namelist()):
        if not name.endswith(".py") or name.endswith("/"):
            continue
        source = archive.read(name).decode("utf-8")
        tree = ast.parse(source, filename=name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.partition(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots.add(node.module.partition(".")[0])
    return roots


def audit_wheel_imports(
    distribution: str,
    observed: set[str],
    *,
    import_root: str,
    declared_import_roots: set[str],
) -> tuple[str, ...]:
    external = observed - set(sys.stdlib_module_names) - {import_root}
    undeclared = sorted(external - declared_import_roots)
    if undeclared:
        raise RuntimeError(f"undeclared import in {distribution}: {', '.join(undeclared)}")
    unobserved = sorted(declared_import_roots - external)
    if unobserved:
        raise RuntimeError(
            f"declared dependency import not observed in {distribution}: {', '.join(unobserved)}"
        )
    return tuple(sorted(external))


def wheel_content_record(archive: zipfile.ZipFile) -> tuple[str, int, int]:
    rows: list[dict[str, str | int]] = []
    total = 0
    for info in sorted(
        (item for item in archive.infolist() if not item.is_dir()),
        key=lambda item: item.filename,
    ):
        data = archive.read(info.filename)
        total += len(data)
        rows.append(
            {
                "path": info.filename,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
        )
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    return hashlib.sha256(payload).hexdigest(), len(rows), total


def check_package(
    distribution: str,
    package: dict[str, str],
    *,
    packages: dict[str, dict[str, str]],
    dependency_graph: dict[str, tuple[str, ...]],
    python_requires: str,
    python_spec: str,
    uv: str,
    tests: bool,
) -> dict[str, object]:
    package_root = (REPOSITORY_ROOT / package["path"]).resolve()
    if package_root.parent != (REPOSITORY_ROOT / "packages").resolve():
        raise RuntimeError(f"package path escapes packages/: {package_root}")

    with tempfile.TemporaryDirectory(prefix=f"utils-{distribution}-") as temporary:
        temporary_root = Path(temporary)
        snapshot = temporary_root / "package"
        dist_dir = temporary_root / "dist"
        environment = temporary_root / "venv"
        copy_package_snapshot(package_root, snapshot)
        run(
            [
                uv,
                "build",
                "--wheel",
                "--out-dir",
                str(dist_dir),
                "--no-create-gitignore",
                "--python",
                python_spec,
                str(snapshot),
            ],
            cwd=temporary_root,
        )
        wheels = sorted(dist_dir.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one wheel for {distribution}, found {len(wheels)}")
        wheel = wheels[0]
        with zipfile.ZipFile(wheel) as archive:
            members = archive.namelist()
            import_prefix = f"{package['import']}/"
            if not any(member.startswith(import_prefix) for member in members):
                raise RuntimeError(f"wheel is missing import root {import_prefix}")
            if any(member.startswith("utils/") for member in members):
                raise RuntimeError("wheel exposes prohibited top-level utils import")
            name, version, requires_python, metadata_dependencies = wheel_metadata(archive)
            if name != distribution:
                raise RuntimeError(
                    f"wheel distribution mismatch: expected {distribution}, observed {name}"
                )
            if version != package["version"]:
                raise RuntimeError(
                    f"wheel version mismatch for {distribution}: expected {package['version']}, "
                    f"observed {version}"
                )
            if requires_python != python_requires:
                raise RuntimeError(
                    f"wheel Python baseline mismatch for {distribution}: "
                    f"expected {python_requires}, observed {requires_python}"
                )
            source_dependencies = dependency_graph[distribution]
            if metadata_dependencies != source_dependencies:
                raise RuntimeError(
                    f"wheel dependency metadata differs for {distribution}: "
                    f"source={source_dependencies}, wheel={metadata_dependencies}"
                )
            declared_import_roots = {
                packages[dependency]["import"] for dependency in metadata_dependencies
            }
            external_imports = audit_wheel_imports(
                distribution,
                imported_roots_from_wheel(archive),
                import_root=package["import"],
                declared_import_roots=declared_import_roots,
            )
            content_root, member_count, uncompressed_bytes = wheel_content_record(archive)

        run(
            [uv, "venv", "--no-project", "--python", python_spec, str(environment)],
            cwd=REPOSITORY_ROOT,
        )
        interpreter = environment_python(environment)
        run(
            [uv, "pip", "install", "--python", str(interpreter), "--no-deps", str(wheel)],
            cwd=REPOSITORY_ROOT,
        )
        probe = (
            f"import {package['import']} as package; "
            f"assert package.__version__ == {package['version']!r}; "
            "print(package.__version__)"
        )
        result = run([str(interpreter), "-I", "-c", probe], cwd=temporary_root)
        record: dict[str, object] = {
            "distribution": distribution,
            "import": package["import"],
            "version": result.stdout.strip(),
            "wheel": wheel.name,
            "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "wheel_content_root_sha256": content_root,
            "wheel_members": member_count,
            "wheel_uncompressed_bytes": uncompressed_bytes,
            "python": python_spec,
            "declared_dependencies": list(metadata_dependencies),
            "observed_external_imports": list(external_imports),
            "dependency_audit": "passed",
            "test_source": "isolated-package-snapshot",
        }
        tests_root = snapshot / "tests"
        if tests and tests_root.is_dir():
            test_result = run(
                [
                    str(interpreter),
                    "-I",
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    str(tests_root),
                    "-p",
                    "test_*.py",
                    "-v",
                ],
                cwd=temporary_root,
            )
            record["tests"] = test_result.stdout.strip().splitlines()[-1]
        return record


def main() -> int:
    parser = argparse.ArgumentParser()
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--package")
    selection.add_argument("--all", action="store_true")
    parser.add_argument("--python", default=sys.executable, dest="python_spec")
    parser.add_argument("--tests", action="store_true")
    args = parser.parse_args()

    uv = require_uv()
    matrix = load_matrix()
    packages = package_records(matrix)
    dependency_graph = audit_dependency_graph(packages)
    selected = sorted(packages) if args.all else [args.package]
    unknown = [name for name in selected if name not in packages]
    if unknown:
        parser.error(f"unknown package: {', '.join(unknown)}")

    python_requires = matrix.get("python_requires")
    if not isinstance(python_requires, str):
        raise RuntimeError("package matrix is missing python_requires")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected)) as executor:
        futures = {
            name: executor.submit(
                check_package,
                name,
                packages[name],
                packages=packages,
                dependency_graph=dependency_graph,
                python_requires=python_requires,
                python_spec=args.python_spec,
                uv=uv,
                tests=args.tests,
            )
            for name in selected
        }
        results = [futures[name].result() for name in selected]
    print(json.dumps({"results": results}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
