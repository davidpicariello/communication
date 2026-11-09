#!/usr/bin/env python3
"""Create a self-contained HTML slide presentation from a JSON source file."""

from __future__ import annotations

import base64
import html
import argparse
import json
import mimetypes
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates"
STYLE_DIR = ROOT / "styles"
THEMES = {path.stem for path in (STYLE_DIR / "themes").glob("*.css")}
SIZES = {path.stem for path in (STYLE_DIR / "sizes").glob("*.css")}


def read_template(path: Path) -> dict:
    """Read layout metadata and HTML markup from a safe YAML document."""
    try:
        metadata = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"{path.name}: invalid YAML: {error}") from error
    if not isinstance(metadata, dict):
        raise ValueError(f"{path.name}: template must be a mapping")
    for key in ("name", "description", "body"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"{path.name}: '{key}' must be a non-empty string")
    fields = metadata.get("fields")
    if not isinstance(fields, list) or any(not isinstance(field, dict) for field in fields):
        raise ValueError(f"{path.name}: 'fields' must be a list of mappings")
    for field in fields:
        if not isinstance(field.get("name"), str) or not field["name"].strip():
            raise ValueError(f"{path.name}: each field requires a non-empty string 'name'")
        if not isinstance(field.get("required", True), bool):
            raise ValueError(f"{path.name}: field '{field['name']}' requires a boolean 'required'")
    metadata["body"] = metadata["body"].strip()
    metadata["id"] = path.stem
    return metadata


def templates() -> list[dict]:
    result = [read_template(path) for path in sorted(TEMPLATE_DIR.glob("*.yaml"))]
    if not result:
        raise RuntimeError(f"No YAML templates found in {TEMPLATE_DIR}")
    preferred_order = ["title", "agenda", "section", "text-bullets", "two-column", "comparison", "timeline", "image-text", "quote", "statistic"]
    rank = {name: index for index, name in enumerate(preferred_order)}
    return sorted(result, key=lambda item: rank.get(str(item["id"]), len(rank)))


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def image_data_uri(value: str) -> str:
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


def render_field(field_type: str, value: object) -> str:
    if field_type == "image":
        return image_data_uri(str(value)) if value else ""
    if field_type == "bullets":
        items = value if isinstance(value, list) else []
        return "\n".join(f"<li>{esc(item)}</li>" for item in items)
    text = esc(value).replace("\n", "<br>" if field_type == "text" else "\n")
    return text


def render_slide(template: dict, values: dict[str, object]) -> str:
    body = str(template["body"])
    fields = template["fields"]
    assert isinstance(fields, list)
    for field in fields:
        assert isinstance(field, dict)
        name = str(field["name"])
        token = "{{" + name + "}}"
        replacement = render_field(str(field.get("type", "text")), values.get(name, ""))
        body = body.replace(token, replacement)
    return f'<section class="slide layout-{esc(template["id"])}">\n{body}\n</section>'


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


def validate_source(source: object) -> dict:
    """Validate and normalize a JSON presentation source document."""
    if not isinstance(source, dict):
        raise ValueError("Presentation JSON must be an object")
    title = source.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("'title' must be a non-empty string")
    theme = source.get("theme", "light")
    if theme not in THEMES:
        raise ValueError(f"'theme' must be one of: {', '.join(sorted(THEMES))}")
    size = source.get("size", "widescreen")
    if size not in SIZES:
        raise ValueError(f"'size' must be one of: {', '.join(sorted(SIZES))}")
    slides_source = source.get("slides")
    if not isinstance(slides_source, list) or not slides_source:
        raise ValueError("'slides' must be a non-empty array")

    available = {str(template["id"]): template for template in templates()}
    slides = []
    for index, slide_source in enumerate(slides_source, start=1):
        if not isinstance(slide_source, dict):
            raise ValueError(f"Slide {index} must be an object")
        layout = slide_source.get("layout")
        if layout not in available:
            raise ValueError(f"Slide {index} has unknown layout {layout!r}")
        values = slide_source.get("values", {})
        if not isinstance(values, dict):
            raise ValueError(f"Slide {index} 'values' must be an object")
        if any(not isinstance(name, str) for name in values):
            raise ValueError(f"Slide {index} field names must be strings")
        template = available[layout]
        fields = template["fields"]
        assert isinstance(fields, list)
        known_fields = {str(field["name"]): field for field in fields if isinstance(field, dict)}
        unknown_fields = set(values) - known_fields.keys()
        if unknown_fields:
            names = ", ".join(sorted(map(str, unknown_fields)))
            raise ValueError(f"Slide {index} ({layout}) has unknown field(s): {names}")
        normalized: dict[str, object] = {}
        for name, field in known_fields.items():
            value = values.get(name, "")
            required = field.get("required", True)
            if required and (value is None or value == "" or value == []):
                raise ValueError(f"Slide {index} ({layout}) requires '{name}'")
            field_type = field.get("type", "text")
            if field_type == "bullets":
                if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                    raise ValueError(f"Slide {index} field '{name}' must be an array of strings")
                max_items = field_limit(field, "max_items")
                if max_items is not None and len(value) > max_items:
                    raise ValueError(
                        f"Slide {index} ({layout}) field '{name}' has {len(value)} items; maximum is {max_items}"
                    )
                max_item_chars = field_limit(field, "max_item_chars")
                if max_item_chars is not None:
                    for item_index, item in enumerate(value, start=1):
                        if len(item) > max_item_chars:
                            raise ValueError(
                                f"Slide {index} ({layout}) field '{name}' item {item_index} has {len(item)} characters; "
                                f"maximum is {max_item_chars}"
                            )
            elif not isinstance(value, str):
                raise ValueError(f"Slide {index} field '{name}' must be a string")
            else:
                max_chars = field_limit(field, "max_chars")
                if max_chars is not None and len(value) > max_chars:
                    raise ValueError(
                        f"Slide {index} ({layout}) field '{name}' has {len(value)} characters; maximum is {max_chars}"
                    )
            normalized[name] = value
        slides.append({"layout": layout, "values": normalized})
    return {"title": title, "theme": theme, "size": size, "slides": slides}


def render_source(source: dict) -> str:
    """Build a deck from validated source data, embedding its safe JSON source."""
    normalized = validate_source(source)
    available = {str(template["id"]): template for template in templates()}
    rendered = [
        render_slide(available[slide["layout"]], slide["values"])
        for slide in normalized["slides"]
    ]
    return make_deck(
        normalized["title"],
        normalized["theme"],
        normalized["size"],
        rendered,
        source_data=normalized,
    )


def css_bundle(theme: str, size: str) -> str:
    files = [STYLE_DIR / "base.css", STYLE_DIR / "themes" / f"{theme}.css", STYLE_DIR / "sizes" / f"{size}.css"]
    return "\n".join(path.read_text(encoding="utf-8") for path in files)


def make_deck(title: str, theme: str, size: str, slides: list[str], *, source_data: dict | None = None) -> str:
    style = css_bundle(theme, size)
    title_html = esc(title)
    slides_html = "\n".join(slides)
    source_html = ""
    if source_data is not None:
        source_json = json.dumps(source_data, ensure_ascii=False).replace("<", "\\u003c")
        source_html = f'  <script type="application/json" id="presentation-source">{source_json}</script>\n'
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title_html}</title>
  <style>\n{style}\n</style>
</head>
<body data-theme="{esc(theme)}">
  <main class="deck" aria-label="{title_html}">
{slides_html}
  </main>
  {source_html}  <nav class="controls" aria-label="Presentation controls">
    <button type="button" id="previous" aria-label="Previous slide">←</button>
    <span id="counter" role="button" tabindex="0" aria-label="Choose a slide" aria-haspopup="true" aria-expanded="false" aria-controls="slide-picker" aria-live="polite"></span>
    <button type="button" id="next" aria-label="Next slide">→</button>
    <div id="slide-picker" class="slide-picker" role="group" aria-label="Choose a slide" hidden></div>
  </nav>
  <script>
    (() => {{
      const slides = [...document.querySelectorAll('.slide')];
      let current = 0;
      const counter = document.getElementById('counter');
      const controls = document.querySelector('.controls');
      const picker = document.getElementById('slide-picker');
      const choices = slides.map((slide, index) => {{
        const heading = slide.querySelector('h1, h2, h3, blockquote, .statistic-value');
        const label = heading?.textContent.trim().replace(/\\s+/g, ' ').slice(0, 80) || `Slide ${{index + 1}}`;
        const choice = document.createElement('button');
        choice.type = 'button';
        choice.className = 'slide-choice';
        choice.textContent = `${{index + 1}}. ${{label}}`;
        choice.setAttribute('aria-label', `Go to slide ${{index + 1}}: ${{label}}`);
        choice.addEventListener('click', () => {{
          show(index);
          setPickerOpen(false);
        }});
        picker.append(choice);
        return choice;
      }});
      function setPickerOpen(open) {{
        picker.hidden = !open;
        counter.setAttribute('aria-expanded', String(open));
      }}
      function show(index) {{
        current = Math.max(0, Math.min(index, slides.length - 1));
        slides.forEach((slide, i) => slide.classList.toggle('active', i === current));
        choices.forEach((choice, i) => choice.setAttribute('aria-current', String(i === current)));
        counter.textContent = `${{current + 1}} / ${{slides.length}}`;
      }}
      controls.addEventListener('click', (event) => {{
        if (event.target.closest('button')) return;
        setPickerOpen(picker.hidden);
      }});
      document.addEventListener('click', (event) => {{
        if (picker.hidden || picker.contains(event.target)) return;
        if (controls.contains(event.target) && !event.target.closest('button')) return;
        setPickerOpen(false);
      }});
      counter.addEventListener('keydown', (event) => {{
        if (event.key === 'Enter' || event.key === ' ') {{
          event.preventDefault();
          event.stopPropagation();
          setPickerOpen(picker.hidden);
        }}
      }});
      document.getElementById('previous').addEventListener('click', () => show(current - 1));
      document.getElementById('next').addEventListener('click', () => show(current + 1));
      document.addEventListener('keydown', (event) => {{
        if (event.key === 'Escape' && !picker.hidden) {{ setPickerOpen(false); return; }}
        if (['ArrowRight', 'PageDown', ' '].includes(event.key)) {{ event.preventDefault(); show(current + 1); }}
        if (['ArrowLeft', 'PageUp'].includes(event.key)) {{ event.preventDefault(); show(current - 1); }}
        if (event.key === 'Home') show(0);
        if (event.key === 'End') show(slides.length - 1);
      }});
      show(0);
    }})();
  </script>
</body>
</html>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a self-contained HTML slide presentation from JSON.")
    parser.add_argument("source", type=Path, help="JSON file describing the presentation")
    parser.add_argument("-o", "--output", type=Path, help="output HTML path (defaults to the source filename with .html)")
    args = parser.parse_args()
    source_path = args.source.expanduser()
    output = (args.output.expanduser() if args.output else source_path.with_suffix(".html"))
    try:
        source = json.loads(source_path.read_text(encoding="utf-8"))
        deck = render_source(source)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(deck, encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Could not create presentation: {error}", file=sys.stderr)
        return 1
    print(f"\nCreated {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
