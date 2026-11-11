"""Field type handlers and the registry used by the presentation builder."""

from .base import FieldType, esc
from .bullets import BulletsFieldType
from .image import ImageFieldType
from .text import HeadingFieldType, TextFieldType

FIELD_TYPES: dict[str, FieldType] = {
    "heading": HeadingFieldType(),
    "text": TextFieldType(),
    "bullets": BulletsFieldType(),
    "image": ImageFieldType(),
}


def register_field_type(name: str, handler: FieldType) -> None:
    """Register a field type handler under the name used in YAML templates."""
    if not name or not name.strip():
        raise ValueError("Field type name must not be empty")
    if name in FIELD_TYPES:
        raise ValueError(f"Field type {name!r} is already registered")
    if not isinstance(handler, FieldType):
        raise TypeError("Field type handler must be a FieldType instance")
    FIELD_TYPES[name] = handler


def get_field_type(name: str) -> FieldType:
    """Return a registered handler or raise a clear unsupported-type error."""
    try:
        return FIELD_TYPES[name]
    except KeyError as error:
        raise ValueError(f"Unsupported field type {name!r}") from error


__all__ = [
    "FIELD_TYPES",
    "FieldType",
    "esc",
    "get_field_type",
    "register_field_type",
]
