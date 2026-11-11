"""Image field type and local-image embedding helper."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from .base import StringFieldType


def image_data_uri(value: str) -> str:
    """Read an image file and encode it as a self-contained data URI."""
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.is_file():
        raise ValueError(f"Image file not found: {value}")
    mime, _ = mimetypes.guess_type(path.name)
    if not mime or not mime.startswith("image/"):
        raise ValueError(f"Not a recognized image file: {value}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class ImageFieldType(StringFieldType):
    def render(self, value: object, field: dict) -> str:
        return image_data_uri(str(value)) if value else ""
