#!/usr/bin/env python3
"""Build, install, and import one or all utility distributions in isolation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPOSITORY_ROOT / "tools" / "package_matrix.json"
TOOLCHAIN_PATH = REPOSITORY_ROOT / "tools" / "toolchain.json"


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


def check_package(
    distribution: str,
    package: dict[str, str],
    *,
    python_spec: str,
    uv: str,
    tests: bool,
) -> dict[str, str]:
    package_root = (REPOSITORY_ROOT / package["path"]).resolve()
    if package_root.parent != (REPOSITORY_ROOT / "packages").resolve():
        raise RuntimeError(f"package path escapes packages/: {package_root}")

    with tempfile.TemporaryDirectory(prefix=f"utils-{distribution}-") as temporary:
        temporary_root = Path(temporary)
        dist_dir = temporary_root / "dist"
        environment = temporary_root / "venv"
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
                str(package_root),
            ],
            cwd=REPOSITORY_ROOT,
        )
        wheels = sorted(dist_dir.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one wheel for {distribution}, found {len(wheels)}")
        wheel = wheels[0]
        with zipfile.ZipFile(wheel) as archive:
            members = archive.namelist()
        import_root = f"{package['import']}/"
        if not any(member.startswith(import_root) for member in members):
            raise RuntimeError(f"wheel is missing import root {import_root}")
        if any(member.startswith("utils/") for member in members):
            raise RuntimeError("wheel exposes prohibited top-level utils import")

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
        record = {
            "distribution": distribution,
            "import": package["import"],
            "version": result.stdout.strip(),
            "wheel": wheel.name,
            "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "python": python_spec,
        }
        tests_root = package_root / "tests"
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
    packages = matrix["packages"]
    assert isinstance(packages, dict)
    selected = sorted(packages) if args.all else [args.package]
    unknown = [name for name in selected if name not in packages]
    if unknown:
        parser.error(f"unknown package: {', '.join(unknown)}")

    results = [
        check_package(
            name,
            packages[name],
            python_spec=args.python_spec,
            uv=uv,
            tests=args.tests,
        )
        for name in selected
    ]
    print(json.dumps({"results": results}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
