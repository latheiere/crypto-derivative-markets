"""Structured errors raised by the public CDM APIs."""

from __future__ import annotations


class CDMError(Exception):
    """Base class for errors produced by this package."""


class ValidationError(CDMError, ValueError):
    """A value does not satisfy a versioned CDM contract."""

    def __init__(self, code: str, path: str, message: str) -> None:
        self.code = code
        self.path = path
        self.message = message
        super().__init__(f"{code} at {path}: {message}")


class DecodeError(ValidationError):
    """Serialized input cannot be decoded into a typed CDM value."""


class UnknownSchemaError(DecodeError):
    """Serialized input identifies an unsupported schema version."""

    def __init__(self, schema_id: object, path: str = "$.schema_id") -> None:
        super().__init__(
            "unsupported_schema",
            path,
            f"schema identifier {schema_id!r} is not supported",
        )
