"""Immutable typed models generated from the frozen selected schema graph."""

from __future__ import annotations

import json
import operator
import re
from collections.abc import Iterator, Mapping
from dataclasses import field, fields, make_dataclass
from enum import StrEnum
from typing import Any, Literal, Self

from .compatibility import PINNED_PROTOCOL, _load_json, _packaged_protocol_root

_OPERATION_SCHEMA_FILES = (
    "v2/ThreadStartParams.json",
    "v2/ThreadStartResponse.json",
    "v2/ThreadResumeParams.json",
    "v2/ThreadResumeResponse.json",
    "v2/ThreadReadParams.json",
    "v2/ThreadReadResponse.json",
    "v2/ThreadListParams.json",
    "v2/ThreadListResponse.json",
    "v2/TurnStartParams.json",
    "v2/TurnStartResponse.json",
    "v2/TurnSteerParams.json",
    "v2/TurnSteerResponse.json",
    "v2/TurnInterruptParams.json",
    "v2/TurnInterruptResponse.json",
    "v2/ReviewStartParams.json",
    "v2/ReviewStartResponse.json",
)
_NOTIFICATION_SCHEMA_FILES = (
    "v2/ErrorNotification.json",
    "v2/WarningNotification.json",
    "v2/DeprecationNoticeNotification.json",
    "v2/ThreadStartedNotification.json",
    "v2/ThreadStatusChangedNotification.json",
    "v2/ThreadClosedNotification.json",
    "v2/TurnStartedNotification.json",
    "v2/TurnCompletedNotification.json",
    "v2/TurnDiffUpdatedNotification.json",
    "v2/TurnPlanUpdatedNotification.json",
    "v2/ItemStartedNotification.json",
    "v2/ItemCompletedNotification.json",
    "v2/AgentMessageDeltaNotification.json",
    "v2/PlanDeltaNotification.json",
    "v2/ReasoningSummaryTextDeltaNotification.json",
)
_CALLBACK_SCHEMA_FILES = (
    "CommandExecutionRequestApprovalParams.json",
    "CommandExecutionRequestApprovalResponse.json",
    "FileChangeRequestApprovalParams.json",
    "FileChangeRequestApprovalResponse.json",
    "ToolRequestUserInputParams.json",
    "ToolRequestUserInputResponse.json",
)
_PUBLIC_SCHEMA_FILES = (
    *_OPERATION_SCHEMA_FILES,
    *_NOTIFICATION_SCHEMA_FILES,
    *_CALLBACK_SCHEMA_FILES,
)
_INTERNAL_SCHEMA_FILES = ("v1/InitializeParams.json", "v1/InitializeResponse.json")
_INBOUND_SCHEMA_FILES = (
    *(path for path in _OPERATION_SCHEMA_FILES if path.endswith("Response.json")),
    *_NOTIFICATION_SCHEMA_FILES,
    *(path for path in _CALLBACK_SCHEMA_FILES if path.endswith("Params.json")),
    "v1/InitializeResponse.json",
)
_PUBLIC_MODEL_NAMES = tuple(
    path.removeprefix("v2/").removesuffix(".json") for path in _PUBLIC_SCHEMA_FILES
)
_INTEGER_FORMAT_BOUNDS = {
    "int32": (-(2**31), 2**31 - 1),
    "int64": (-(2**63), 2**63 - 1),
    "uint": (0, 2**64 - 1),
    "uint16": (0, 2**16 - 1),
    "uint32": (0, 2**32 - 1),
    "uint64": (0, 2**64 - 1),
}


class _ModelValidationError(ValueError):
    """Content-free selected-schema model validation failure."""


def _freeze_json(value: object, path: str) -> object:
    if value is None or isinstance(value, (bool, int, float, str, StrEnum)):
        return value
    if isinstance(value, _SchemaModel):
        return value
    if isinstance(value, Mapping):
        return FrozenJsonObject(value, _path=path)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, f"{path}[]") for item in value)
    raise _ModelValidationError(f"{path} contains a non-JSON value")


class FrozenJsonObject(Mapping[str, object]):
    """Deeply immutable JSON object used only where the schema permits openness."""

    __slots__ = ("_items", "_lookup")

    def __init__(self, value: Mapping[str, object] | None = None, *, _path: str = "object") -> None:
        source = value or {}
        if not all(isinstance(key, str) for key in source):
            raise _ModelValidationError(f"{_path} contains a non-string key")
        items = tuple((key, _freeze_json(item, f"{_path}.{key}")) for key, item in source.items())
        self._items = items
        self._lookup = dict(items)

    def __getitem__(self, key: str) -> object:
        return self._lookup[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._lookup)

    def __len__(self) -> int:
        return len(self._lookup)

    def __repr__(self) -> str:
        return f"FrozenJsonObject(keys={tuple(self._lookup)})"


JsonValue = None | bool | int | float | str | tuple["JsonValue", ...] | FrozenJsonObject


class _SchemaModel:
    __slots__ = ()

    _schema_name: str

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> Self:
        decoded = _decode_named(cls._schema_name, value, cls._schema_name)
        if not isinstance(decoded, cls):
            raise _ModelValidationError(f"{cls.__name__} did not decode to its frozen class")
        return decoded

    def to_dict(self) -> dict[str, object]:
        return _model_to_dict(self)


class _ModelSpec:
    __slots__ = ("name", "schema", "root", "source", "sources", "canonical")

    def __init__(
        self,
        name: str,
        schema: Mapping[str, object],
        root: Mapping[str, object],
        source: str,
    ) -> None:
        self.name = name
        self.schema = schema
        self.root = root
        self.source = source
        self.sources = {source}
        self.canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))


def _allows_additional_properties(spec: _ModelSpec) -> bool:
    if "additionalProperties" in spec.schema:
        return spec.schema["additionalProperties"] is not False
    return not spec.sources.isdisjoint(_INBOUND_SCHEMA_FILES)


def _collect_model_specs(
    documents: Mapping[str, Mapping[str, object]],
) -> dict[str, _ModelSpec]:
    specs: dict[str, _ModelSpec] = {}
    visited_refs: set[tuple[str, str]] = set()

    def register(
        name: str,
        schema: Mapping[str, object],
        root: Mapping[str, object],
        source: str,
    ) -> None:
        if not name.isidentifier():
            raise _ModelValidationError(f"selected schema has an invalid model name: {name!r}")
        candidate = _ModelSpec(name, schema, root, source)
        prior = specs.get(name)
        if prior is not None:
            if prior.canonical != candidate.canonical:
                raise _ModelValidationError(
                    f"selected schemas define unequal models with the same name: {name}"
                )
            prior.sources.add(source)
            return
        specs[name] = candidate

    def visit(node: object, root: Mapping[str, object], source: str) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item, root, source)
            return
        if not isinstance(node, Mapping):
            return
        title = node.get("title")
        if isinstance(title, str) and (
            node.get("enum") is not None or node.get("type") == "object" or "properties" in node
        ):
            register(title, node, root, source)
        reference = node.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/definitions/"):
            name = reference.removeprefix("#/definitions/")
            marker = (source, name)
            if marker not in visited_refs:
                visited_refs.add(marker)
                definitions = root.get("definitions")
                if not isinstance(definitions, Mapping) or not isinstance(
                    definitions.get(name), Mapping
                ):
                    raise _ModelValidationError(f"selected schema references missing model: {name}")
                definition = definitions[name]
                register(name, definition, root, source)
                visit(definition, root, source)
        for key, child in node.items():
            if key not in {"$ref", "definitions"}:
                visit(child, root, source)

    for source, root in documents.items():
        title = root.get("title")
        if not isinstance(title, str):
            raise _ModelValidationError(f"selected schema document has no title: {source}")
        top = {key: value for key, value in root.items() if key != "definitions"}
        register(title, top, root, source)
        visit(top, root, source)

    initialize = documents["v1/InitializeParams.json"]
    definitions = initialize.get("definitions")
    client_info = definitions.get("ClientInfo") if isinstance(definitions, Mapping) else None
    if not isinstance(client_info, Mapping):
        raise _ModelValidationError("initialize schema has no ClientInfo definition")
    register("ClientIdentity", client_info, initialize, "v1/InitializeParams.json")
    return specs


def _load_documents() -> dict[str, Mapping[str, object]]:
    root = _packaged_protocol_root().joinpath("upstream", PINNED_PROTOCOL.codex_version)
    return {
        path: _load_json(root.joinpath(path), f"selected model schema {path}")
        for path in (*_PUBLIC_SCHEMA_FILES, *_INTERNAL_SCHEMA_FILES)
    }


_DOCUMENTS = _load_documents()
_SPECS = _collect_model_specs(_DOCUMENTS)
_RUNTIME_TYPES: dict[str, object] = {}


def _is_object_schema(schema: Mapping[str, object]) -> bool:
    return (schema.get("type") == "object" or "properties" in schema) and not any(
        key in schema for key in ("oneOf", "anyOf", "allOf")
    )


def _enum_members(values: list[object]) -> dict[str, str]:
    if not all(isinstance(value, str) for value in values):
        raise _ModelValidationError("selected string enum contains a non-string value")
    members: dict[str, str] = {}
    for value in values:
        base = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper() or "VALUE"
        if base[0].isdigit():
            base = f"VALUE_{base}"
        name = base
        suffix = 2
        while name in members and members[name] != value:
            name = f"{base}_{suffix}"
            suffix += 1
        members[name] = value
    return members


def _annotation(schema: object, root: Mapping[str, object]) -> str:
    if schema is True:
        return "JsonValue"
    if schema is False or not isinstance(schema, Mapping):
        return "object"
    if not schema:
        return "JsonValue"
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/definitions/"):
        return reference.removeprefix("#/definitions/")
    title = schema.get("title")
    if isinstance(title, str) and title in _SPECS:
        return title
    variants = schema.get("oneOf", schema.get("anyOf"))
    if isinstance(variants, list):
        return " | ".join(dict.fromkeys(_annotation(item, root) for item in variants))
    all_of = schema.get("allOf")
    if isinstance(all_of, list) and all_of:
        return _annotation(all_of[0], root)
    enum = schema.get("enum")
    if isinstance(enum, list):
        return "Literal[" + ", ".join(repr(value) for value in enum) + "]"
    expected = schema.get("type")
    if isinstance(expected, list):
        return " | ".join(dict.fromkeys(_annotation({"type": item}, root) for item in expected))
    if expected == "null":
        return "None"
    if expected == "boolean":
        return "bool"
    if expected == "integer":
        return "int"
    if expected == "number":
        return "int | float"
    if expected == "string":
        return "str"
    if expected == "array":
        return f"tuple[{_annotation(schema.get('items', True), root)}, ...]"
    if expected == "object" or "properties" in schema:
        return "FrozenJsonObject"
    return "object"


def _model_post_init(self: _SchemaModel) -> None:
    spec = _SPECS[self._schema_name]
    properties = spec.schema.get("properties", {})
    required = spec.schema.get("required", [])
    if not isinstance(properties, Mapping) or not isinstance(required, list):
        raise _ModelValidationError(f"{self._schema_name} has malformed object constraints")
    for name, child_schema in properties.items():
        value = getattr(self, name)
        if name not in required and value is None:
            continue
        normalized = _decode(child_schema, spec.root, value, f"{self._schema_name}.{name}")
        object.__setattr__(self, name, normalized)
    if hasattr(self, "additional_properties"):
        extras = self.additional_properties
        if not isinstance(extras, Mapping):
            raise _ModelValidationError(
                f"{self._schema_name}.additional_properties must be a mapping"
            )
        overlap = set(extras).intersection(properties)
        if overlap:
            raise _ModelValidationError(
                f"{self._schema_name}.additional_properties repeats declared fields"
            )
        additional_schema = spec.schema.get("additionalProperties", True)
        normalized = {
            key: _decode(
                additional_schema if isinstance(additional_schema, Mapping) else True,
                spec.root,
                value,
                f"{self._schema_name}.{key}",
            )
            for key, value in extras.items()
        }
        object.__setattr__(self, "additional_properties", FrozenJsonObject(normalized))


def _make_models() -> None:
    for name, spec in _SPECS.items():
        enum = spec.schema.get("enum")
        if isinstance(enum, list):
            enum_type = StrEnum(name, _enum_members(enum), module=__name__)
            globals()[name] = enum_type
            _RUNTIME_TYPES[name] = enum_type

    for name, spec in _SPECS.items():
        if name in _RUNTIME_TYPES or not _is_object_schema(spec.schema):
            continue
        properties = spec.schema.get("properties", {})
        required = spec.schema.get("required", [])
        if not isinstance(properties, Mapping) or not isinstance(required, list):
            raise _ModelValidationError(f"{name} has malformed object constraints")
        model_fields: list[tuple[Any, ...]] = []
        property_order = (
            ("name", "version", "title") if name == "ClientIdentity" else tuple(properties)
        )
        for property_name in property_order:
            child_schema = properties[property_name]
            annotation = _annotation(child_schema, spec.root)
            if property_name in required:
                model_fields.append((property_name, annotation))
            else:
                if "None" not in annotation.split(" | "):
                    annotation = f"{annotation} | None"
                model_fields.append((property_name, annotation, field(default=None)))
        if _allows_additional_properties(spec):
            if "additional_properties" in properties:
                raise _ModelValidationError(f"{name} conflicts with the open-object field name")
            model_fields.append(
                (
                    "additional_properties",
                    "FrozenJsonObject",
                    field(default_factory=FrozenJsonObject, repr=False),
                )
            )
        model = make_dataclass(
            name,
            model_fields,
            bases=(_SchemaModel,),
            namespace={
                "__module__": __name__,
                "__doc__": f"Frozen model for the retained {name} schema.",
                "_schema_name": name,
                "__post_init__": _model_post_init,
            },
            frozen=True,
            slots=True,
            kw_only=name != "ClientIdentity",
        )
        globals()[name] = model
        _RUNTIME_TYPES[name] = model

    for name in _SPECS:
        if name not in _RUNTIME_TYPES:
            alias = _runtime_type(_SPECS[name].schema, _SPECS[name].root, resolving={name})
            globals()[name] = alias
            _RUNTIME_TYPES[name] = alias


def _union_type(types: list[object]) -> object:
    unique: list[object] = []
    for item in types:
        if item not in unique:
            unique.append(item)
    if not unique:
        return object
    result = unique[0]
    for item in unique[1:]:
        result = operator.or_(result, item)
    return result


def _runtime_type(
    schema: object,
    root: Mapping[str, object],
    *,
    resolving: set[str] | None = None,
) -> object:
    resolving = set() if resolving is None else resolving
    if schema is True:
        return JsonValue
    if schema is False or not isinstance(schema, Mapping):
        return object
    if not schema:
        return JsonValue
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/definitions/"):
        name = reference.removeprefix("#/definitions/")
        if name in _RUNTIME_TYPES:
            return _RUNTIME_TYPES[name]
        if name in resolving:
            return object
        spec = _SPECS[name]
        return _runtime_type(spec.schema, spec.root, resolving=resolving | {name})
    title = schema.get("title")
    if isinstance(title, str) and title in _RUNTIME_TYPES:
        return _RUNTIME_TYPES[title]
    variants = schema.get("oneOf", schema.get("anyOf"))
    if isinstance(variants, list):
        return _union_type([_runtime_type(item, root, resolving=resolving) for item in variants])
    all_of = schema.get("allOf")
    if isinstance(all_of, list) and all_of:
        return _runtime_type(all_of[0], root, resolving=resolving)
    enum = schema.get("enum")
    if isinstance(enum, list):
        return Literal[tuple(enum)]
    expected = schema.get("type")
    if isinstance(expected, list):
        return _union_type(
            [_runtime_type({"type": item}, root, resolving=resolving) for item in expected]
        )
    if expected == "null":
        return type(None)
    if expected == "boolean":
        return bool
    if expected == "integer":
        return int
    if expected == "number":
        return int | float
    if expected == "string":
        return str
    if expected == "array":
        return tuple[_runtime_type(schema.get("items", True), root, resolving=resolving), ...]
    if expected == "object" or "properties" in schema:
        return FrozenJsonObject
    return object


def _decode_named(name: str, value: object, path: str) -> object:
    runtime_type = _RUNTIME_TYPES.get(name)
    if isinstance(runtime_type, type) and isinstance(value, runtime_type):
        return value
    spec = _SPECS.get(name)
    if spec is None:
        raise _ModelValidationError(f"{path} references an unavailable frozen model")
    return _decode(spec.schema, spec.root, value, path, expected_name=name)


def _decode(
    schema: object,
    root: Mapping[str, object],
    value: object,
    path: str,
    *,
    expected_name: str | None = None,
) -> object:
    if schema is True:
        return _freeze_json(value, path)
    if schema is False or not isinstance(schema, Mapping):
        raise _ModelValidationError(f"{path} is forbidden by the retained schema")
    if not schema:
        return _freeze_json(value, path)
    reference = schema.get("$ref")
    if isinstance(reference, str):
        if not reference.startswith("#/definitions/"):
            raise _ModelValidationError(f"{path} uses an unsupported schema reference")
        return _decode_named(reference.removeprefix("#/definitions/"), value, path)
    title = schema.get("title")
    if expected_name is None and isinstance(title, str) and title in _SPECS:
        return _decode_named(title, value, path)
    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        if not all_of:
            raise _ModelValidationError(f"{path} has an empty allOf")
        decoded = _decode(all_of[0], root, value, path)
        for item in all_of[1:]:
            _decode(item, root, value, path)
        return decoded
    variants = schema.get("oneOf")
    if isinstance(variants, list):
        matches: list[object] = []
        for item in variants:
            try:
                matches.append(_decode(item, root, value, path))
            except _ModelValidationError:
                continue
        if len(matches) != 1:
            raise _ModelValidationError(f"{path} does not match exactly one closed variant")
        return matches[0]
    variants = schema.get("anyOf")
    if isinstance(variants, list):
        for item in variants:
            try:
                return _decode(item, root, value, path)
            except _ModelValidationError:
                pass
        raise _ModelValidationError(f"{path} does not match a closed variant")
    enum = schema.get("enum")
    if isinstance(enum, list):
        if value not in enum:
            raise _ModelValidationError(f"{path} is not a selected enum value")
        if expected_name is not None:
            enum_type = _RUNTIME_TYPES.get(expected_name)
            if isinstance(enum_type, type) and issubclass(enum_type, StrEnum):
                return enum_type(value)
        return value
    expected = schema.get("type")
    if isinstance(expected, list):
        for item in expected:
            try:
                return _decode({**schema, "type": item}, root, value, path)
            except _ModelValidationError:
                pass
        raise _ModelValidationError(f"{path} has the wrong closed JSON type")
    if expected == "null":
        if value is not None:
            raise _ModelValidationError(f"{path} must be null")
        return None
    if expected == "boolean":
        if not isinstance(value, bool):
            raise _ModelValidationError(f"{path} must be boolean")
        return value
    if expected == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise _ModelValidationError(f"{path} must be integer")
        _validate_number_constraints(schema, value, path)
        return value
    if expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _ModelValidationError(f"{path} must be number")
        _validate_number_constraints(schema, value, path)
        return value
    if expected == "string":
        if not isinstance(value, str):
            raise _ModelValidationError(f"{path} must be string")
        minimum = schema.get("minLength")
        if isinstance(minimum, int) and len(value) < minimum:
            raise _ModelValidationError(f"{path} is shorter than the retained minimum")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            raise _ModelValidationError(f"{path} does not match the retained pattern")
        return value
    if expected == "array":
        if not isinstance(value, (list, tuple)):
            raise _ModelValidationError(f"{path} must be array")
        return tuple(_decode(schema.get("items", True), root, item, f"{path}[]") for item in value)
    if expected == "object" or "properties" in schema:
        return _decode_object(schema, root, value, path, expected_name=expected_name)
    raise _ModelValidationError(f"{path} has an unsupported retained schema shape")


def _validate_number_constraints(
    schema: Mapping[str, object], value: int | float, path: str
) -> None:
    integer_format = schema.get("format")
    if integer_format in _INTEGER_FORMAT_BOUNDS:
        lower, upper = _INTEGER_FORMAT_BOUNDS[integer_format]
        if value < lower or value > upper:
            raise _ModelValidationError(f"{path} is outside the retained {integer_format} range")
    minimum = schema.get("minimum")
    if isinstance(minimum, (int, float)) and value < minimum:
        raise _ModelValidationError(f"{path} is below the retained minimum")
    maximum = schema.get("maximum")
    if isinstance(maximum, (int, float)) and value > maximum:
        raise _ModelValidationError(f"{path} is above the retained maximum")


def _decode_object(
    schema: Mapping[str, object],
    root: Mapping[str, object],
    value: object,
    path: str,
    *,
    expected_name: str | None,
) -> object:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise _ModelValidationError(f"{path} must be an object with string keys")
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(properties, Mapping) or not isinstance(required, list):
        raise _ModelValidationError(f"{path} has malformed object constraints")
    missing = [name for name in required if name not in value]
    if missing:
        raise _ModelValidationError(f"{path} is missing required fields")
    unknown = set(value).difference(properties)
    additional = schema.get("additionalProperties", False)
    if (
        "additionalProperties" not in schema
        and expected_name is not None
        and _allows_additional_properties(_SPECS[expected_name])
    ):
        additional = True
    if unknown and additional is False:
        raise _ModelValidationError(f"{path} contains unselected fields")
    decoded = {
        name: _decode(child_schema, root, value[name], f"{path}.{name}")
        for name, child_schema in properties.items()
        if name in value
    }
    extras = {
        name: _decode(
            additional if isinstance(additional, Mapping) else True,
            root,
            value[name],
            f"{path}.{name}",
        )
        for name in unknown
    }
    if expected_name is not None:
        runtime_type = _RUNTIME_TYPES.get(expected_name)
        if isinstance(runtime_type, type) and issubclass(runtime_type, _SchemaModel):
            if additional is not False:
                decoded["additional_properties"] = FrozenJsonObject(extras)
            return runtime_type(**decoded)
    return FrozenJsonObject({**decoded, **extras}, _path=path)


def _model_to_dict(model: _SchemaModel) -> dict[str, object]:
    spec = _SPECS[model._schema_name]
    properties = spec.schema.get("properties", {})
    required = spec.schema.get("required", [])
    result: dict[str, object] = {}
    for item in fields(model):
        if item.name == "additional_properties":
            continue
        value = getattr(model, item.name)
        if item.name not in required and value is None:
            continue
        result[item.name] = _to_json(value)
    if hasattr(model, "additional_properties"):
        for key, value in model.additional_properties.items():
            if key in properties:
                raise _ModelValidationError(f"{model._schema_name} has an extra-field collision")
            result[key] = _to_json(value)
    return result


def _to_json(value: object) -> object:
    if isinstance(value, _SchemaModel):
        return _model_to_dict(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, FrozenJsonObject):
        return {key: _to_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_to_json(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise _ModelValidationError("model contains a non-JSON value")


def _decode_document(source: str, value: object) -> _SchemaModel:
    root = _DOCUMENTS[source]
    title = root.get("title")
    if not isinstance(title, str):
        raise _ModelValidationError("selected document has no model title")
    decoded = _decode_named(title, value, title)
    if not isinstance(decoded, _SchemaModel):
        raise _ModelValidationError(f"{title} did not decode to an immutable model")
    return decoded


_make_models()

__all__: list[str] = list(("ClientIdentity", *_PUBLIC_MODEL_NAMES))  # noqa: F822
