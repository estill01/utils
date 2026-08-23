"""Public app-server client error taxonomy."""


class AppServerClientError(Exception):
    """Base class for every public client failure."""


class CodexBinaryNotFoundError(AppServerClientError):
    """No executable resolved from the explicit path or PATH."""


class AmbiguousCodexBinaryError(AppServerClientError):
    """More than one distinct executable resolved from PATH."""


class CodexVersionError(AppServerClientError):
    """The executable version could not be probed or is incompatible."""


class SchemaMissingError(AppServerClientError):
    """A required schema root, file, or definition is missing."""


class SchemaMalformedError(AppServerClientError):
    """A schema file is not valid JSON or has an invalid structure."""


class SchemaRootMismatchError(AppServerClientError):
    """A byte, semantic, selected-surface, or API root is incompatible."""


class UnsupportedFeatureError(AppServerClientError):
    """A required selected feature is absent from the compatible schema."""
