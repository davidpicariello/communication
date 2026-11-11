"""Image field type and local-image embedding helper."""

from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path

from .base import StringFieldType

DATA_URI_PATTERN = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/]*={0,2})$")


def validate_image_data_uri(value: str) -> bool:
    """Return whether value is a valid base64 data URI for an image."""
    match = DATA_URI_PATTERN.fullmatch(value)
    if not match:
        return False
    try:
        base64.b64decode(match.group(2), validate=True)
    except ValueError:
        return False
    return True


def image_data_uri(value: str) -> str:
    """Read an image file and encode it as a self-contained data URI."""
    if value.startswith("data:"):
        if not validate_image_data_uri(value):
            raise ValueError("Not a recognized image data URI")
        return value

    path = Path(value).expanduser()
    if not path.is_absolute():
        working_path = Path.cwd() / path
        if working_path.is_file():
            path = working_path
        else:
            path = next(
                (parent / path for parent in Path(__file__).resolve().parents if (parent / path).is_file()),
                working_path,
            )
    if not path.is_file():
        raise ValueError(f"Image file not found: {value}")
    mime, _ = mimetypes.guess_type(path.name)
    if not mime or not mime.startswith("image/"):
        raise ValueError(f"Not a recognized image file: {value}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class ImageFieldType(StringFieldType):
    def validate(self, value: object, field: dict, *, location: str) -> str:
        # Embedded images can be much longer than the path-length limit in templates.
        if isinstance(value, str) and value.startswith("data:"):
            if not validate_image_data_uri(value):
                raise ValueError(f"{location} must be an image path or a valid base64 image data URI")
            return value
        return super().validate(value, field, location=location)

    def render(self, value: object, field: dict) -> str:
        return image_data_uri(str(value)) if value else ""
