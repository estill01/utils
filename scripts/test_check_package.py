#!/usr/bin/env python3
"""Deterministic negative tests for the isolated-wheel audit."""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import check_package


class PackageIsolationAuditTests(unittest.TestCase):
    def test_requirement_names_are_normalized_without_external_parser(self) -> None:
        self.assertEqual(
            check_package.requirement_distribution(
                "Example_Package[feature]>=1; python_version>'3'"
            ),
            "example-package",
        )
        with self.assertRaisesRegex(RuntimeError, "invalid runtime requirement"):
            check_package.requirement_distribution("!!!")

    def test_unadmitted_dependencies_fail_without_consumer_knowledge(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "unadmitted runtime dependency.*requests"):
            check_package.audit_dependency_edges("neutral", ("requests",), {"neutral"})

    def test_dependency_contract_preserves_versions_markers_and_urls(self) -> None:
        pairs = [
            (("peer==1",), ("peer==2",)),
            (("peer; python_version < '3.13'",), ("peer; python_version >= '3.13'",)),
            (
                ("peer @ https://example.invalid/one.whl",),
                ("peer @ https://example.invalid/two.whl",),
            ),
        ]
        for expected, observed in pairs:
            with (
                self.subTest(observed=observed),
                self.assertRaisesRegex(RuntimeError, "runtime dependency contract differs"),
            ):
                check_package.audit_requirement_contract(
                    "neutral",
                    expected=expected,
                    observed=observed,
                    source="source",
                )

    def test_admitted_peer_edge_cannot_self_authorize_from_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            roots: dict[str, Path] = {}
            packages: dict[str, dict[str, object]] = {}
            for distribution, dependencies in (
                ("alpha", ["beta>=1"]),
                ("beta", []),
            ):
                package_root = root / distribution
                package_root.mkdir()
                (package_root / "pyproject.toml").write_text(
                    (
                        "[project]\n"
                        f'name = "{distribution}"\n'
                        'version = "1"\n'
                        f"dependencies = {dependencies!r}\n"
                    ),
                    encoding="utf-8",
                )
                roots[distribution] = package_root
                packages[distribution] = {
                    "path": f"packages/{distribution}",
                    "import": distribution,
                    "version": "1",
                    "runtime_dependencies": (),
                }
            with self.assertRaisesRegex(RuntimeError, "source runtime dependency contract differs"):
                check_package.audit_dependency_graph(packages, roots)

    def test_all_matrix_paths_are_contained_before_metadata_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packages_root = root / "packages"
            packages_root.mkdir()
            valid = packages_root / "valid"
            valid.mkdir()
            outside = root / "outside"
            outside.mkdir()
            records = {
                "selected": {
                    "path": "packages/valid",
                    "import": "valid",
                    "version": "1",
                    "runtime_dependencies": (),
                },
                "unselected": {
                    "path": "../outside",
                    "import": "outside",
                    "version": "1",
                    "runtime_dependencies": (),
                },
            }
            with self.assertRaisesRegex(RuntimeError, "package path escapes packages/.*unselected"):
                check_package.validate_package_paths(records, repository_root=root)

            records["unselected"]["path"] = "packages/link"
            (packages_root / "link").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, "package root must be a real directory"):
                check_package.validate_package_paths(records, repository_root=root)

    def test_circular_dependencies_include_the_exact_cycle(self) -> None:
        graph = {"alpha": ("beta",), "beta": ("gamma",), "gamma": ("alpha",)}
        with self.assertRaisesRegex(
            RuntimeError, "circular package dependency: alpha -> beta -> gamma -> alpha"
        ):
            check_package.validate_acyclic_graph(graph)

    def test_undeclared_and_unobserved_imports_fail_clearly(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "undeclared import.*third_party"):
            check_package.audit_wheel_imports(
                "neutral",
                {"neutral", "json", "third_party"},
                import_root="neutral",
                declared_import_roots=set(),
            )
        with self.assertRaisesRegex(RuntimeError, "declared dependency import not observed"):
            check_package.audit_wheel_imports(
                "neutral",
                {"neutral", "json"},
                import_root="neutral",
                declared_import_roots={"declared_dependency"},
            )

    def test_wheel_import_scan_ignores_relative_imports(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(
                "neutral/__init__.py",
                "from .model import Record\nimport json\nimport third_party.module\n",
            )
        buffer.seek(0)
        with zipfile.ZipFile(buffer) as archive:
            self.assertEqual(
                check_package.imported_roots_from_wheel(archive),
                {"json", "third_party"},
            )

    def test_wheel_metadata_and_content_root_are_exact(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("neutral/__init__.py", "__version__ = '1.2.3'\n")
            archive.writestr(
                "neutral-1.2.3.dist-info/METADATA",
                (
                    "Metadata-Version: 2.3\n"
                    "Name: Neutral_Package\n"
                    "Version: 1.2.3\n"
                    "Requires-Python: >=3.11\n"
                    "Requires-Dist: admitted-dependency>=2\n\n"
                ),
            )
        buffer.seek(0)
        with zipfile.ZipFile(buffer) as archive:
            self.assertEqual(
                check_package.wheel_metadata(archive),
                ("neutral-package", "1.2.3", ">=3.11", ("admitted-dependency>=2",)),
            )
            first = check_package.wheel_content_record(archive)
            second = check_package.wheel_content_record(archive)
        self.assertEqual(first, second)
        self.assertEqual(first[1:], (2, 144))

    def test_package_snapshot_rejects_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "escape").symlink_to(root / "outside")
            with self.assertRaisesRegex(RuntimeError, "package snapshot contains symlink"):
                check_package.copy_package_snapshot(source, root / "snapshot")

    def test_missing_and_empty_test_contracts_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(RuntimeError, "test contract is missing"):
                check_package.require_test_contract(root / "missing")
            empty = root / "empty"
            empty.mkdir()
            with self.assertRaisesRegex(RuntimeError, "test contract is empty"):
                check_package.require_test_contract(empty)
            test_file = empty / "test_present.py"
            test_file.write_text("# test contract marker\n", encoding="utf-8")
            self.assertEqual(check_package.require_test_contract(empty), [test_file])

    def test_executed_test_count_must_be_positive_and_exact(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "executed zero or an unknown test count"):
            check_package.executed_test_count("Ran 0 tests in 0.000s\n\nOK\n")
        with self.assertRaisesRegex(RuntimeError, "executed zero or an unknown test count"):
            check_package.executed_test_count("OK\n")
        self.assertEqual(
            check_package.executed_test_count("Ran 12 tests in 0.025s\n\nOK\n"),
            12,
        )

    def test_retained_package_data_requires_exact_members_and_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package_root = Path(temporary)
            contract = package_root / "contract"
            contract.mkdir()
            (contract / "schema.json").write_bytes(b'{"schema":1}\n')
            (package_root / "pyproject.toml").write_text(
                (
                    "[tool.hatch.build.targets.wheel.force-include]\n"
                    '"contract" = "neutral/_contract"\n'
                ),
                encoding="utf-8",
            )

            def archive_with(resources: dict[str, bytes]) -> zipfile.ZipFile:
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w") as writer:
                    writer.writestr("neutral/__init__.py", "")
                    for name, content in resources.items():
                        writer.writestr(name, content)
                buffer.seek(0)
                archive = zipfile.ZipFile(buffer)
                self.addCleanup(buffer.close)
                self.addCleanup(archive.close)
                return archive

            with self.assertRaisesRegex(RuntimeError, "package-data members differ.*missing"):
                check_package.audit_forced_package_data(
                    package_root,
                    archive_with({}),
                    import_root="neutral",
                )
            with self.assertRaisesRegex(RuntimeError, "package-data bytes differ"):
                check_package.audit_forced_package_data(
                    package_root,
                    archive_with({"neutral/_contract/schema.json": b"changed\n"}),
                    import_root="neutral",
                )
            with self.assertRaisesRegex(RuntimeError, "package-data members differ.*extra"):
                check_package.audit_forced_package_data(
                    package_root,
                    archive_with(
                        {
                            "neutral/_contract/schema.json": b'{"schema":1}\n',
                            "neutral/_contract/extra.json": b"{}\n",
                        }
                    ),
                    import_root="neutral",
                )
            retained_root, retained_count = check_package.audit_forced_package_data(
                package_root,
                archive_with({"neutral/_contract/schema.json": b'{"schema":1}\n'}),
                import_root="neutral",
            )
            self.assertEqual(retained_count, 1)
            self.assertRegex(retained_root, r"^[0-9a-f]{64}$")

    def test_child_failure_includes_bounded_captured_output(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporary,
            self.assertRaisesRegex(RuntimeError, "DETAIL") as raised,
        ):
            check_package.run(
                [
                    sys.executable,
                    "-c",
                    "print('DETAIL'); raise SystemExit(7)",
                ],
                cwd=Path(temporary),
            )
        self.assertIn("exit 7", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
