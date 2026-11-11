"""Heading and plain-text field types."""

from .base import StringFieldType, esc


class HeadingFieldType(StringFieldType):
    def render(self, value: object, field: dict) -> str:
        return esc(value)


class TextFieldType(StringFieldType):
    def render(self, value: object, field: dict) -> str:
        return esc(value).replace("\n", "<br>")
