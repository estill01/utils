from __future__ import annotations

import ast
import inspect
import json
import re
import unittest
from dataclasses import FrozenInstanceError
from importlib.resources import files
from pathlib import Path

import runtime_manifest as manifest
import runtime_manifest.testing as manifest_testing
from runtime_manifest import (
    Capability,
    CompatibilityReport,
    Component,
    ManifestDecodeError,
    ManifestError,
    ManifestValidationError,
    Protocol,
    RuntimeManifest,
    Sha256Root,
    UnavailableKind,
    UnsupportedSchemaError,
    canonical_json,
    compare_manifests,
    parse_manifest,
)
from runtime_manifest.testing import neutral_expected, neutral_incompatible, neutral_observed

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
A = "a" * 64
B = "b" * 64
C = "c" * 64


def contract_json(name: str) -> dict[str, object]:
    resource = files("runtime_manifest").joinpath("_contract", name)
    if resource.is_file():
        return json.loads(resource.read_text(encoding="utf-8"))
    return json.loads((PACKAGE_ROOT / "contract" / name).read_text(encoding="utf-8"))


class ImmutableModelTests(unittest.TestCase):
    def test_manifest_normalizes_all_unordered_records(self) -> None:
        value = RuntimeManifest(
            component=Component("engine", "1", Sha256Root(A)),
            protocols=(
                Protocol("wire", "1", Sha256Root(B), ("status", "cancel")),
                Protocol("events", "1", Sha256Root(C)),
            ),
            capabilities=(Capability("status", "1"), Capability("cancel", "1")),
            dependencies=(
                Component("queue", "1", Sha256Root(B)),
                Component("codec", "1", Sha256Root(C)),
            ),
        )
        self.assertEqual([item.name for item in value.protocols], ["events", "wire"])
        self.assertEqual(value.protocols[1].features, ("cancel", "status"))
        self.assertEqual([item.name for item in value.capabilities], ["cancel", "status"])
        self.assertEqual([item.name for item in value.dependencies], ["codec", "queue"])
        with self.assertRaises(FrozenInstanceError):
            value.schema_version = 2  # type: ignore[misc]

    def test_roots_names_versions_and_exact_types_are_bounded(self) -> None:
        for root in ("A" * 64, "a" * 63, "g" * 64, 1, None):
            with self.subTest(root=root), self.assertRaises(ManifestValidationError):
                Sha256Root(root)  # type: ignore[arg-type]
        for name in ("", "Upper", "a/b", "-leading", "x" * 129):
            with self.subTest(name=name), self.assertRaises(ManifestValidationError):
                Capability(name, "1")
        for version in ("", "line\nbreak", "x" * 129, 1, None):
            with self.subTest(version=version), self.assertRaises(ManifestValidationError):
                Capability("feature", version)  # type: ignore[arg-type]

    def test_duplicate_records_features_and_self_dependencies_reject(self) -> None:
        component = Component("engine", "1", Sha256Root(A))
        protocol = Protocol("wire", "1", Sha256Root(B))
        capability = Capability("status", "1")
        invalid_arguments = (
            {"protocols": (protocol, protocol)},
            {"capabilities": (capability, capability)},
            {"dependencies": (component,)},
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments), self.assertRaises(ManifestValidationError):
                RuntimeManifest(component, **arguments)
        with self.assertRaises(ManifestValidationError):
            Protocol("wire", "1", Sha256Root(B), ("status", "status"))
        with self.assertRaises(ManifestValidationError):
            RuntimeManifest(component, protocols=[protocol])  # type: ignore[arg-type]

    def test_schema_version_is_exact_and_fail_closed(self) -> None:
        component = Component("engine", "1", Sha256Root(A))
        with self.assertRaises(ManifestValidationError):
            RuntimeManifest(component, schema_version=True)
        with self.assertRaises(UnsupportedSchemaError):
            RuntimeManifest(component, schema_version=2)

    def test_unicode_scalars_and_aggregate_limits_are_enforced(self) -> None:
        limits = contract_json("public-api.json")["resource_limits"]
        with self.assertRaises(ManifestValidationError):
            Capability("feature", "\ud800")
        with self.assertRaisesRegex(ManifestValidationError, "32-item limit"):
            Protocol(
                "wire",
                "1",
                Sha256Root(A),
                (object(),) * (limits["features_per_protocol"] + 1),  # type: ignore[arg-type]
            )
        component = Component("engine", "1", Sha256Root(A))
        bounded_collections = (
            ("protocols", (object(),) * (limits["protocols"] + 1), limits["protocols"]),
            (
                "capabilities",
                (object(),) * (limits["capabilities"] + 1),
                limits["capabilities"],
            ),
            (
                "dependencies",
                (object(),) * (limits["dependencies"] + 1),
                limits["dependencies"],
            ),
        )
        for field, values, maximum in bounded_collections:
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(ManifestValidationError, f"{maximum}-item limit"),
            ):
                RuntimeManifest(component, **{field: values})


class CanonicalSerializationTests(unittest.TestCase):
    def test_canonical_json_is_sorted_compact_stable_and_round_trips(self) -> None:
        expected = neutral_expected()
        encoded = canonical_json(expected)
        self.assertTrue(encoded.endswith("\n"))
        self.assertFalse(encoded.endswith("\n\n"))
        self.assertNotIn(": ", encoded)
        self.assertEqual(encoded, canonical_json(parse_manifest(encoded)))
        self.assertEqual(parse_manifest(encoded.encode("utf-8")), expected)
        decoded = json.loads(encoded)
        self.assertEqual(
            set(decoded),
            {"schema_version", "component", "protocols", "capabilities", "dependencies"},
        )
        self.assertEqual(decoded["component"]["content_root"], f"sha256:{A}")

    def test_unknown_authority_and_product_fields_reject_at_every_boundary(self) -> None:
        base = json.loads(canonical_json(neutral_expected()))
        for field in ("authorization", "acceptance", "product_id", "discovery"):
            candidate = json.loads(json.dumps(base))
            candidate[field] = True
            with self.subTest(field=field), self.assertRaises(ManifestDecodeError):
                parse_manifest(json.dumps(candidate))
        nested = json.loads(json.dumps(base))
        nested["component"]["acceptance"] = "approved"
        with self.assertRaises(ManifestDecodeError):
            parse_manifest(json.dumps(nested))

    def test_duplicate_fields_nonfinite_values_and_bad_utf8_reject(self) -> None:
        duplicate = canonical_json(neutral_expected()).replace(
            '"schema_version":1',
            '"schema_version":1,"schema_version":1',
        )
        for value in (duplicate, "NaN", b"\xff"):
            with self.subTest(value=repr(value)), self.assertRaises(ManifestDecodeError):
                parse_manifest(value)

    def test_unknown_schema_and_shape_errors_are_discriminated(self) -> None:
        value = json.loads(canonical_json(neutral_expected()))
        value["schema_version"] = 2
        with self.assertRaises(UnsupportedSchemaError):
            parse_manifest(json.dumps(value))
        value["schema_version"] = True
        with self.assertRaises(ManifestDecodeError):
            parse_manifest(json.dumps(value))
        value["schema_version"] = 1.0
        with self.assertRaises(ManifestDecodeError):
            parse_manifest(json.dumps(value))
        for future in (
            {"schema_version": 2, "future_field": True},
            {"schema_version": 2},
        ):
            with self.subTest(future=future), self.assertRaises(UnsupportedSchemaError):
                parse_manifest(json.dumps(future))

    def test_surrogates_oversized_documents_and_recursion_fail_as_decode_errors(self) -> None:
        invalid_scalar = canonical_json(neutral_expected()).replace('"1.0"', '"\\ud800"', 1)
        limits = contract_json("public-api.json")["resource_limits"]
        oversized = canonical_json(neutral_expected()) + " " * limits["document_utf8_bytes"]
        hostile_oversized_text = "\ud800" + "x" * limits["document_utf8_bytes"]
        nested = "[" * 1000 + "]" * 1000
        oversized_integer = "9" * 5000
        for value in (
            invalid_scalar,
            invalid_scalar.encode("utf-8"),
            oversized,
            oversized.encode("utf-8"),
            nested,
            nested.encode("utf-8"),
            oversized_integer,
            oversized_integer.encode("utf-8"),
        ):
            with (
                self.subTest(kind=type(value).__name__, length=len(value)),
                self.assertRaises(ManifestDecodeError),
            ):
                parse_manifest(value)
        with self.assertRaisesRegex(ManifestDecodeError, "exceeds the UTF-8 byte limit"):
            parse_manifest(hostile_oversized_text)

        base = json.loads(canonical_json(neutral_expected()))
        for field, maximum in (
            ("protocols", limits["protocols"]),
            ("capabilities", limits["capabilities"]),
            ("dependencies", limits["dependencies"]),
        ):
            candidate = json.loads(json.dumps(base))
            candidate[field] = [None] * (maximum + 1)
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(ManifestDecodeError, f"{maximum}-item limit"),
            ):
                parse_manifest(json.dumps(candidate))
        feature_overflow = json.loads(json.dumps(base))
        feature_overflow["protocols"][0]["features"] = [None] * (
            limits["features_per_protocol"] + 1
        )
        with self.assertRaisesRegex(
            ManifestDecodeError,
            f"{limits['features_per_protocol']}-item limit",
        ):
            parse_manifest(json.dumps(feature_overflow))

    def test_maximum_valid_manifest_fits_the_document_limit_and_round_trips(self) -> None:
        limits = contract_json("public-api.json")["resource_limits"]
        maximum_text = "\U0010ffff" * 128

        def name(prefix: str, index: int) -> str:
            start = f"{prefix}{index:02d}"
            return start + prefix * (128 - len(start))

        features = tuple(name("f", index) for index in range(limits["features_per_protocol"]))
        value = RuntimeManifest(
            Component("engine", maximum_text, Sha256Root(A)),
            protocols=tuple(
                Protocol(name("p", index), maximum_text, Sha256Root(B), features)
                for index in range(limits["protocols"])
            ),
            capabilities=tuple(
                Capability(name("c", index), maximum_text)
                for index in range(limits["capabilities"])
            ),
            dependencies=tuple(
                Component(name("d", index), maximum_text, Sha256Root(C))
                for index in range(limits["dependencies"])
            ),
        )
        encoded = canonical_json(value).encode("utf-8")
        self.assertLessEqual(len(encoded), limits["document_utf8_bytes"])
        self.assertEqual(parse_manifest(encoded), value)
        value = json.loads(canonical_json(neutral_expected()))
        value["protocols"][0]["features"] = "ordered"
        with self.assertRaises(ManifestDecodeError):
            parse_manifest(json.dumps(value))


class CompatibilityTests(unittest.TestCase):
    def test_observed_superset_satisfies_exact_descriptive_requirements(self) -> None:
        report = compare_manifests(neutral_expected(), neutral_observed())
        self.assertTrue(report.compatible)
        self.assertEqual(report.unavailable_reasons, ())

    def test_mismatches_project_closed_deterministic_reasons(self) -> None:
        report = compare_manifests(neutral_expected(), neutral_incompatible())
        fixture = contract_json("compatibility-fixtures.json")
        expected = fixture["fixtures"]["exact-mismatch-projection"]
        self.assertFalse(report.compatible)
        self.assertEqual(
            [reason.kind.value for reason in report.unavailable_reasons],
            expected["unavailable_kinds"],
        )
        missing = [reason for reason in report.unavailable_reasons if reason.observed is None]
        self.assertTrue(missing)
        self.assertTrue(all(reason.kind.name.endswith("MISSING") for reason in missing))

    def test_component_name_and_capability_version_are_distinct(self) -> None:
        expected = RuntimeManifest(
            Component("engine", "1", Sha256Root(A)),
            capabilities=(Capability("lifecycle", "1"),),
        )
        observed = RuntimeManifest(
            Component("worker", "1", Sha256Root(A)),
            capabilities=(Capability("lifecycle", "2"),),
        )
        self.assertEqual(
            {reason.kind for reason in compare_manifests(expected, observed).unavailable_reasons},
            {UnavailableKind.COMPONENT_NAME, UnavailableKind.CAPABILITY_VERSION},
        )

    def test_comparison_requires_exact_manifests(self) -> None:
        with self.assertRaises(TypeError):
            compare_manifests(neutral_expected(), object())  # type: ignore[arg-type]

    def test_maximum_name_feature_subject_returns_a_report(self) -> None:
        protocol_name = "p" * 128
        feature_name = "f" * 128
        component = Component("engine", "1", Sha256Root(A))
        expected = RuntimeManifest(
            component,
            protocols=(Protocol(protocol_name, "1", Sha256Root(B), (feature_name,)),),
        )
        observed = RuntimeManifest(
            component,
            protocols=(Protocol(protocol_name, "1", Sha256Root(B)),),
        )
        report = compare_manifests(expected, observed)
        self.assertEqual(len(report.unavailable_reasons), 1)
        reason = report.unavailable_reasons[0]
        self.assertEqual(reason.kind, UnavailableKind.FEATURE_MISSING)
        self.assertEqual(len(reason.subject), 257)

    def test_maximum_valid_comparison_has_a_bounded_total_report(self) -> None:
        limits = contract_json("public-api.json")["resource_limits"]
        features = tuple(f"f{index:02d}" for index in range(limits["features_per_protocol"]))
        expected_protocols = tuple(
            Protocol(f"p{index:02d}", "1", Sha256Root(A), features)
            for index in range(limits["protocols"])
        )
        observed_protocols = tuple(
            Protocol(f"p{index:02d}", "2", Sha256Root(B)) for index in range(limits["protocols"])
        )
        expected_dependencies = tuple(
            Component(f"d{index:02d}", "1", Sha256Root(A))
            for index in range(limits["dependencies"])
        )
        observed_dependencies = tuple(
            Component(f"d{index:02d}", "2", Sha256Root(B))
            for index in range(limits["dependencies"])
        )
        expected = RuntimeManifest(
            Component("engine", "1", Sha256Root(A)),
            protocols=expected_protocols,
            capabilities=tuple(
                Capability(f"c{index:02d}", "1") for index in range(limits["capabilities"])
            ),
            dependencies=expected_dependencies,
        )
        observed = RuntimeManifest(
            Component("worker", "2", Sha256Root(B)),
            protocols=observed_protocols,
            dependencies=observed_dependencies,
        )
        report = compare_manifests(expected, observed)
        self.assertEqual(len(report.unavailable_reasons), limits["unavailable_reasons"])
        self.assertFalse(report.compatible)
        self.assertIsInstance(report, CompatibilityReport)


class FrozenPackageContractTests(unittest.TestCase):
    def test_public_api_record_matches_exact_runtime(self) -> None:
        public = contract_json("public-api.json")
        self.assertEqual(public["version"], manifest.__version__)
        self.assertEqual(public["root_exports"], manifest.__all__)
        self.assertEqual(
            public["public_signatures"],
            {
                name: str(inspect.signature(getattr(manifest, name)))
                for name in public["public_signatures"]
            },
        )
        self.assertEqual(
            public["public_properties"],
            {
                "CompatibilityReport.compatible": str(
                    inspect.signature(manifest.CompatibilityReport.compatible.fget)
                )
            },
        )
        self.assertEqual(public["testing_exports"], manifest_testing.__all__)
        self.assertEqual(
            public["testing_signatures"],
            {
                name: str(inspect.signature(getattr(manifest_testing, name)))
                for name in public["testing_signatures"]
            },
        )
        self.assertEqual(
            public["unavailable_kind_values"],
            {kind.name: kind.value for kind in UnavailableKind},
        )
        self.assertEqual(
            public["error_hierarchy"],
            {
                name: [base.__name__ for base in getattr(manifest, name).__bases__]
                for name in public["error_hierarchy"]
            },
        )

    def test_schema_fixture_and_supported_python_records_are_exact(self) -> None:
        schema = contract_json("manifest-schema.json")
        fixtures = contract_json("compatibility-fixtures.json")
        supported = contract_json("supported-python.json")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"], {"const": 1})
        self.assertEqual(schema["$defs"]["root"]["pattern"], "^sha256:[0-9a-f]{64}$")
        limits = contract_json("public-api.json")["resource_limits"]
        self.assertEqual(schema["x-document-max-utf8-bytes"], limits["document_utf8_bytes"])
        for field in ("protocols", "capabilities", "dependencies"):
            self.assertTrue(schema["properties"][field]["uniqueItems"])
            self.assertEqual(schema["properties"][field]["maxItems"], limits[field])
        self.assertEqual(
            schema["$defs"]["protocol"]["properties"]["features"]["maxItems"],
            limits["features_per_protocol"],
        )
        self.assertEqual(len(schema["x-runtime-semantic-invariants"]), 6)
        self.assertIn(
            (
                "schema_version uses the JSON integer representation 1 rather than a "
                "numerically equal non-integer form"
            ),
            schema["x-runtime-semantic-invariants"],
        )
        self.assertIn(
            "all text contains Unicode scalar values only",
            schema["x-runtime-semantic-invariants"],
        )
        text_pattern = re.compile(schema["$defs"]["text"]["pattern"])
        self.assertIsNotNone(text_pattern.search("valid\u2028text"))
        self.assertIsNone(text_pattern.search("a\u2028b\u0001"))
        self.assertIsNone(text_pattern.search("a\u2029b\u0001"))
        self.assertIsNone(text_pattern.search("terminal-newline\n"))
        for fixture in fixtures["fixtures"].values():
            expected = getattr(manifest_testing, fixture["expected_factory"])()
            observed = getattr(manifest_testing, fixture["observed_factory"])()
            report = compare_manifests(expected, observed)
            self.assertEqual(report.compatible, fixture["compatible"])
            self.assertEqual(
                [reason.kind.value for reason in report.unavailable_reasons],
                fixture["unavailable_kinds"],
            )
        self.assertEqual(supported["requires_python"], ">=3.11")
        self.assertEqual(supported["acceptance_interpreters"], ["3.11", "3.14"])

    def test_schema_parser_parity_for_duplicate_and_semantic_invariants(self) -> None:
        schema = contract_json("manifest-schema.json")
        self.assertTrue(schema["properties"]["protocols"]["uniqueItems"])
        base = json.loads(canonical_json(neutral_expected()))
        exact_duplicate = json.loads(json.dumps(base))
        exact_duplicate["protocols"].append(exact_duplicate["protocols"][0])
        duplicate_name = json.loads(json.dumps(base))
        changed = dict(duplicate_name["protocols"][0])
        changed["version"] = "different"
        duplicate_name["protocols"].append(changed)
        self_dependency = json.loads(json.dumps(base))
        self_dependency["dependencies"].append(dict(self_dependency["component"]))
        for candidate in (exact_duplicate, duplicate_name, self_dependency):
            with self.subTest(candidate=candidate), self.assertRaises(ManifestDecodeError):
                parse_manifest(json.dumps(candidate))

    def test_report_limit_record_is_consistent_with_exact_values(self) -> None:
        limits = contract_json("public-api.json")["resource_limits"]
        maximum = limits["unavailable_reasons"]
        with self.assertRaisesRegex(ManifestValidationError, f"{maximum}-item limit"):
            CompatibilityReport((object(),) * (maximum + 1))  # type: ignore[arg-type]

    def test_readme_example_executes_through_public_imports(self) -> None:
        readme = (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8")
        examples = re.findall(r"```python executable\n(.*?)```", readme, flags=re.DOTALL)
        self.assertEqual(len(examples), 1)
        exec(compile(examples[0], "README.md", "exec"), {"__name__": "__docs_example__"})

    def test_runtime_has_no_ambient_discovery_or_downstream_dependency(self) -> None:
        pyproject = (PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)
        prohibited_imports = {"importlib", "os", "pathlib", "pkgutil", "subprocess", "sysconfig"}
        for path in sorted((PACKAGE_ROOT / "src").rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
            imported = {
                alias.name.split(".", 1)[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            } | {
                (node.module or "").split(".", 1)[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            }
            self.assertFalse(imported & prohibited_imports)

    def test_all_manifest_errors_share_the_package_base(self) -> None:
        for error_type in (
            ManifestValidationError,
            ManifestDecodeError,
            UnsupportedSchemaError,
        ):
            self.assertTrue(issubclass(error_type, ManifestError))


if __name__ == "__main__":
    unittest.main()
