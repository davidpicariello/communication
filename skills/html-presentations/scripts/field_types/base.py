"""Shared field type interfaces and validation helpers."""

from __future__ import annotations

import html
from abc import ABC, abstractmethod


def esc(value: object) -> str:
    """Escape a value for safe insertion into HTML text or attributes."""
    return html.escape(str(value), quote=True)


def field_limit(field: dict, key: str) -> int | None:
    """Read and validate a numeric field limit from template metadata."""
    raw_limit = field.get(key)
    if raw_limit is None:
        return None
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Template field '{field.get('name')}' has an invalid {key} limit") from error
    if limit < 0:
        raise ValueError(f"Template field '{field.get('name')}' has a negative {key} limit")
    return limit


class FieldType(ABC):
    """Base handler; implement validation and rendering for a field type."""

    def empty_value(self) -> object:
        """Return the normalized value to use when an optional field is omitted."""
        return ""

    def is_empty(self, value: object) -> bool:
        return value is None or value == self.empty_value()

    @abstractmethod
    def validate(self, value: object, field: dict, *, location: str) -> object:
        """Validate and normalize a JSON value for this field."""

    @abstractmethod
    def render(self, value: object, field: dict) -> str:
        """Render a normalized value for insertion into the template body."""


class StringFieldType(FieldType):
    """Base for field types whose JSON values are strings."""

    def validate(self, value: object, field: dict, *, location: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{location} must be a string")
        max_chars = field_limit(field, "max_chars")
        if max_chars is not None and len(value) > max_chars:
            raise ValueError(f"{location} has {len(value)} characters; maximum is {max_chars}")
        return value
