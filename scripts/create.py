#!/usr/bin/env python3
"""Create a self-contained HTML slide presentation from a JSON source file."""

from __future__ import annotations

import base64
import html
import argparse
import json
import mimetypes
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates"
STYLE_DIR = ROOT / "styles"
THEMES = {"clean", "dark"}
SIZES = {"widescreen", "standard"}


def read_template(path: Path) -> dict:
    """Read simple YAML-like metadata from an HTML comment at file start."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\s*<!--\s*\n(.*?)\n\s*-->\s*\n(.*)", text, re.S)
    if not match:
        raise ValueError(f"{path.name}: missing metadata comment")
    metadata: dict[str, object] = {"fields": []}
    current_field: dict[str, str] | None = None
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            current_field = {}
            metadata["fields"].append(current_field)  # type: ignore[union-attr]
            stripped = stripped[2:]
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            if key.strip() == "fields":
                current_field = None
                metadata["fields"] = []
                continue
            target = current_field if current_field is not None and key in {"name", "label", "type", "required", "placeholder"} else metadata
            target[key.strip()] = value.strip().strip('"\'')
    metadata["body"] = match.group(2).strip()
    metadata["id"] = path.stem
    return metadata


def templates() -> list[dict]:
    result = [read_template(path) for path in sorted(TEMPLATE_DIR.glob("*.html")) if path.name != "index.html"]
    if not result:
        raise RuntimeError(f"No HTML templates found in {TEMPLATE_DIR}")
    preferred_order = ["title", "section", "text-bullets", "two-column", "comparison", "image-text", "quote", "statistic"]
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


def validate_source(source: object) -> dict:
    """Validate and normalize a JSON presentation source document."""
    if not isinstance(source, dict):
        raise ValueError("Presentation JSON must be an object")
    title = source.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("'title' must be a non-empty string")
    theme = source.get("theme", "clean")
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
            required = field.get("required", "true").lower() not in {"false", "no", "0"}
            if required and (value is None or value == "" or value == []):
                raise ValueError(f"Slide {index} ({layout}) requires '{name}'")
            field_type = field.get("type", "text")
            if field_type == "bullets":
                if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                    raise ValueError(f"Slide {index} field '{name}' must be an array of strings")
            elif not isinstance(value, str):
                raise ValueError(f"Slide {index} field '{name}' must be a string")
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
    <span id="counter" aria-live="polite"></span>
    <button type="button" id="next" aria-label="Next slide">→</button>
  </nav>
  <script>
    (() => {{
      const slides = [...document.querySelectorAll('.slide')];
      let current = 0;
      const counter = document.getElementById('counter');
      function show(index) {{
        current = Math.max(0, Math.min(index, slides.length - 1));
        slides.forEach((slide, i) => slide.classList.toggle('active', i === current));
        counter.textContent = `${{current + 1}} / ${{slides.length}}`;
        fitText();
      }}
      function fitText() {{
        const active = slides[current];
        if (!active) return;
        active.querySelectorAll('[data-fit]').forEach((element) => {{
          const max = Number(element.dataset.maxSize || 48);
          const min = Number(element.dataset.minSize || 14);
          element.style.fontSize = `${{max}}px`;
          let size = max;
          while (size > min && (element.scrollHeight > element.clientHeight || element.scrollWidth > element.clientWidth)) {{
            size -= 1;
            element.style.fontSize = `${{size}}px`;
          }}
        }});
      }}
      document.getElementById('previous').addEventListener('click', () => show(current - 1));
      document.getElementById('next').addEventListener('click', () => show(current + 1));
      document.addEventListener('keydown', (event) => {{
        if (['ArrowRight', 'PageDown', ' '].includes(event.key)) {{ event.preventDefault(); show(current + 1); }}
        if (['ArrowLeft', 'PageUp'].includes(event.key)) {{ event.preventDefault(); show(current - 1); }}
        if (event.key === 'Home') show(0);
        if (event.key === 'End') show(slides.length - 1);
      }});
      window.addEventListener('resize', fitText);
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
