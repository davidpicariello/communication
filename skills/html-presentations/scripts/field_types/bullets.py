"""Bullet-list field type."""

from .base import FieldType, field_limit, esc


class BulletsFieldType(FieldType):
    def empty_value(self) -> list[str]:
        return []

    def validate(self, value: object, field: dict, *, location: str) -> list[str]:
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(f"{location} must be an array of strings")
        max_items = field_limit(field, "max_items")
        if max_items is not None and len(value) > max_items:
            raise ValueError(f"{location} has {len(value)} items; maximum is {max_items}")
        max_item_chars = field_limit(field, "max_item_chars")
        if max_item_chars is not None:
            for item_index, item in enumerate(value, start=1):
                if len(item) > max_item_chars:
                    raise ValueError(
                        f"{location} item {item_index} has {len(item)} characters; maximum is {max_item_chars}"
                    )
        return value

    def render(self, value: object, field: dict) -> str:
        items = value if isinstance(value, list) else []
        return "\n".join(f"<li>{esc(item)}</li>" for item in items)
