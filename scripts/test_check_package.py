#!/usr/bin/env python3
"""Deterministic negative tests for the isolated-wheel audit."""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
import warnings
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

    def test_package_tree_symlinks_fail_before_metadata_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packages_root = root / "packages"
            packages_root.mkdir()
            outside = root / "outside.toml"
            outside.write_text("[project]\ndependencies = []\n", encoding="utf-8")
            records = {
                "unselected": {
                    "path": "packages/unselected",
                    "import": "unselected",
                    "version": "1",
                    "runtime_dependencies": (),
                }
            }
            for relative in (Path("pyproject.toml"), Path("contract/schema.json")):
                with self.subTest(relative=relative):
                    package_root = packages_root / "unselected"
                    package_root.mkdir()
                    target = package_root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.symlink_to(outside)
                    with self.assertRaisesRegex(RuntimeError, "package tree contains symlink"):
                        check_package.validate_package_paths(records, repository_root=root)
                    target.unlink()
                    if target.parent != package_root:
                        target.parent.rmdir()
                    package_root.rmdir()

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

    def test_duplicate_wheel_members_are_rejected_before_audit(self) -> None:
        for duplicate in (
            "neutral/__init__.py",
            "neutral/_contract/schema.json",
        ):
            with self.subTest(duplicate=duplicate):
                buffer = io.BytesIO()
                with warnings.catch_warnings(), zipfile.ZipFile(buffer, "w") as archive:
                    warnings.simplefilter("ignore", UserWarning)
                    archive.writestr(duplicate, b"first")
                    archive.writestr(duplicate, b"second")
                buffer.seek(0)
                with (
                    zipfile.ZipFile(buffer) as archive,
                    self.assertRaisesRegex(RuntimeError, "duplicate member name"),
                ):
                    check_package.validated_wheel_member_names(archive)

    def test_unsafe_wheel_directory_entries_are_rejected_before_audit(self) -> None:
        for directory in ("../../escape/", "other/", "neutral//nested/"):
            with self.subTest(directory=directory):
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w") as archive:
                    archive.writestr(directory, b"")
                buffer.seek(0)
                with zipfile.ZipFile(buffer) as archive:
                    if directory == "other/":
                        names = check_package.validated_wheel_member_names(archive)
                        with self.assertRaisesRegex(RuntimeError, "unexpected top-level member"):
                            check_package.audit_wheel_layout(
                                names,
                                distribution="neutral",
                                import_root="neutral",
                                version="1",
                            )
                    else:
                        with self.assertRaisesRegex(RuntimeError, "unsafe member path"):
                            check_package.validated_wheel_member_names(archive)

    def test_wheel_root_files_cannot_masquerade_as_directories(self) -> None:
        for collision in ("neutral", "neutral-1.dist-info"):
            with self.subTest(collision=collision):
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w") as archive:
                    archive.writestr(collision, b"regular file")
                    archive.writestr("neutral/__init__.py", b"")
                    archive.writestr("neutral-1.dist-info/METADATA", b"")
                    archive.writestr("neutral-1.dist-info/RECORD", b"")
                    archive.writestr("neutral-1.dist-info/WHEEL", b"")
                buffer.seek(0)
                with (
                    zipfile.ZipFile(buffer) as archive,
                    self.assertRaisesRegex(RuntimeError, "unexpected top-level member"),
                ):
                    names = check_package.validated_wheel_member_names(archive)
                    check_package.audit_wheel_layout(
                        names,
                        distribution="neutral",
                        import_root="neutral",
                        version="1",
                    )

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("neutral", b"regular file")
            archive.writestr("neutral/", b"")
        buffer.seek(0)
        with (
            zipfile.ZipFile(buffer) as archive,
            self.assertRaisesRegex(RuntimeError, "duplicate member name.*neutral"),
        ):
            check_package.validated_wheel_member_names(archive)

    def test_wheel_metadata_singleton_headers_are_exact(self) -> None:
        for field, conflicting in (
            ("Name", "other"),
            ("Version", "9"),
            ("Requires-Python", ">=9"),
        ):
            with self.subTest(field=field):
                headers = {
                    "Name": "neutral",
                    "Version": "1",
                    "Requires-Python": ">=3.11",
                }
                metadata = "Metadata-Version: 2.3\n" + "".join(
                    f"{name}: {value}\n" for name, value in headers.items()
                )
                metadata += f"{field}: {conflicting}\n\n"
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w") as writer:
                    writer.writestr("neutral-1.dist-info/METADATA", metadata)
                buffer.seek(0)
                with (
                    zipfile.ZipFile(buffer) as archive,
                    self.assertRaisesRegex(RuntimeError, f"exactly one {field} header"),
                ):
                    check_package.wheel_metadata(archive)

    def test_wheel_layout_rejects_combined_and_top_level_modules(self) -> None:
        base = (
            "neutral/__init__.py",
            "neutral-1.dist-info/METADATA",
            "neutral-1.dist-info/RECORD",
            "neutral-1.dist-info/WHEEL",
        )
        for unexpected in ("other/__init__.py", "utils.py"):
            with (
                self.subTest(unexpected=unexpected),
                self.assertRaisesRegex(RuntimeError, "unexpected top-level member"),
            ):
                check_package.audit_wheel_layout(
                    (*base, unexpected),
                    distribution="neutral",
                    import_root="neutral",
                    version="1",
                )

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
            retained_root, retained_count, retained_members = (
                check_package.audit_forced_package_data(
                    package_root,
                    archive_with({"neutral/_contract/schema.json": b'{"schema":1}\n'}),
                    import_root="neutral",
                )
            )
            self.assertEqual(retained_members, frozenset({"neutral/_contract/schema.json"}))
            self.assertEqual(retained_count, 1)
            self.assertRegex(retained_root, r"^[0-9a-f]{64}$")

    def test_build_snapshot_mutation_cannot_rewrite_acceptance_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pristine = root / "pristine"
            build = root / "build"
            (pristine / "tests").mkdir(parents=True)
            (pristine / "tests" / "test_contract.py").write_text(
                "# substantive contract\n", encoding="utf-8"
            )
            (pristine / "contract.json").write_text('{"value":1}\n', encoding="utf-8")
            check_package.copy_package_snapshot(pristine, build)
            expected = check_package.package_snapshot_record(pristine)

            check_package.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "from pathlib import Path; root=Path.cwd(); "
                        "(root/'tests/test_contract.py').write_text('# trivialized\\n'); "
                        "(root/'contract.json').write_text('{\\\"value\\\":2}\\n')"
                    ),
                ],
                cwd=build,
            )

            check_package.verify_snapshot_unchanged(
                pristine,
                expected,
                label="pristine acceptance",
            )
            with self.assertRaisesRegex(
                RuntimeError,
                "build package snapshot changed.*contract.json.*tests/test_contract.py",
            ):
                check_package.verify_snapshot_unchanged(build, expected, label="build")

    def test_source_package_files_must_match_pristine_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package_root = Path(temporary)
            source_root = package_root / "src" / "neutral"
            source_root.mkdir(parents=True)
            (source_root / "__init__.py").write_bytes(b"VALUE = 1\n")

            def archive_with(files: dict[str, bytes]) -> zipfile.ZipFile:
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w") as writer:
                    for name, content in files.items():
                        writer.writestr(name, content)
                buffer.seek(0)
                archive = zipfile.ZipFile(buffer)
                self.addCleanup(buffer.close)
                self.addCleanup(archive.close)
                return archive

            with self.assertRaisesRegex(RuntimeError, "source bytes differ"):
                check_package.audit_source_package_files(
                    package_root,
                    archive_with({"neutral/__init__.py": b"VALUE = 2\n"}),
                    import_root="neutral",
                    retained_members=frozenset(),
                )
            with self.assertRaisesRegex(RuntimeError, "source members differ.*extra"):
                check_package.audit_source_package_files(
                    package_root,
                    archive_with(
                        {
                            "neutral/__init__.py": b"VALUE = 1\n",
                            "neutral/injected.py": b"INJECTED = True\n",
                        }
                    ),
                    import_root="neutral",
                    retained_members=frozenset(),
                )
            source_hash, source_count = check_package.audit_source_package_files(
                package_root,
                archive_with({"neutral/__init__.py": b"VALUE = 1\n"}),
                import_root="neutral",
                retained_members=frozenset(),
            )
            self.assertEqual(source_count, 1)
            self.assertRegex(source_hash, r"^[0-9a-f]{64}$")

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
