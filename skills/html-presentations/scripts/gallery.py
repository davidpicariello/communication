#!/usr/bin/env python3
"""Generate an offline HTML catalog of available slide layouts."""

from __future__ import annotations

import html
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parents[1]
spec = importlib.util.spec_from_file_location("presentation_create", ROOT / "scripts" / "create.py")
assert spec and spec.loader
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def example_text(field: dict) -> str:
    example = field.get("example", "")
    if field.get("type") == "bullets" and example:
        return " · ".join(example)
    return str(example)


def field_details(field: dict) -> str:
    details = [str(field.get("type", "text"))]
    if field.get("required", True) is False:
        details.append("optional")
    if field.get("type") == "bullets":
        if "max_items" in field:
            details.append(f"max {field['max_items']} items")
        if "max_item_chars" in field:
            details.append(f"max {field['max_item_chars']} chars/item")
    elif "max_chars" in field:
        details.append(f"max {field['max_chars']} chars")
    return ", ".join(details)


def main() -> None:
    templates = builder.templates()
    previews: list[str] = []
    for template in templates:
        values: dict[str, object] = {}
        fields = template["fields"]
        for field in fields:
            field_type = field.get("type", "text")
            example = field.get("example")
            if example is not None:
                if field_type == "bullets":
                    values[field["name"]] = example
                elif field_type == "image" and example:
                    image_path = Path(example)
                    values[field["name"]] = str(
                        image_path if image_path.is_absolute() else REPOSITORY_ROOT / image_path
                    )
                else:
                    values[field["name"]] = example
            elif field_type == "bullets":
                values[field["name"]] = ["A concise example point", "Another supporting point"]
            elif field_type == "image":
                # Gallery is self-contained without depending on external image tooling.
                values[field["name"]] = ""
            else:
                values[field["name"]] = {
                    "title": template["name"],
                    "quote": "A memorable idea, clearly expressed.",
                    "value": "42%",
                    "left_heading": "Option A",
                    "right_heading": "Option B",
                    "left_content": "A focused example of content.",
                    "right_content": "A complementary example.",
                    "description": "A sample description to show the layout.",
                    "subtitle": "A miniature layout preview",
                    "presenter": "Example presentation",
                    "attribution": "Example source",
                    "source": "Illustrative example",
                    "alt": "Example image preview",
                    "content": "Example text demonstrates this layout.\nIt can span multiple lines.",
                    "intro": "A brief introduction to the key points.",
                    "message": "Make the most of what you learned.",
                    "action": "Start with the first step today.",
                    "contact": "Questions? hello@example.com",
                }.get(field["name"], "Example content")
        preview_slide = builder.render_slide(template, values)
        safe_id = html.escape(str(template["id"]), quote=True)
        fields_html_parts = []
        for field in fields:
            field_info = (
                f"<li><code>{html.escape(str(field['name']))}</code> — {html.escape(str(field.get('label', field['name'])))} "
                f"<small>({html.escape(field_details(field))})</small>"
            )
            example = example_text(field)
            if example:
                field_info += f"<br><small>Example: {html.escape(example)}</small>"
            fields_html_parts.append(field_info + "</li>")
        fields_html = "".join(fields_html_parts)
        previews.append(f'''<article class="template-card" id="{safe_id}">
  <header><h2>{html.escape(str(template['name']))}</h2><p>{html.escape(str(template['description']))}</p></header>
  <div class="preview">{preview_slide}</div>
  <details><summary>Fields and input types</summary><ul>{fields_html}</ul></details>
</article>''')

    css = builder.css_bundle("light", "widescreen")
    # Scale a live slide to fit the card without adding a screenshot dependency.
    gallery_css = css + "\n" + """
    body { display:block; min-height:100vh; height:auto; overflow:auto; padding:36px; background:#edf0f6; }
    .gallery { width:max-content; margin:0 auto; }
    .gallery h1 { font-size:42px; }
    .gallery-grid { display:grid; grid-template-columns:repeat(3, 600px); gap:24px; }
    .template-card { width:600px; margin:0; padding:24px; border-radius:16px; background:white; box-shadow:0 8px 30px #17203312; }
    .template-card header p { color:#657187; }
    .preview { position:relative; width:min(100%,720px); aspect-ratio:16/9; overflow:hidden; margin:18px 0; border:1px solid #dce2ed; }
    .preview .slide { display:flex; inset:0; width:100%; height:100%; padding:7.5% 8%; }
    .preview .slide h1 { font-size:clamp(22px,5vw,52px); }
    .preview .slide h2 { font-size:clamp(18px,3vw,32px); }
    .preview .slide h3 { font-size:clamp(14px,2vw,23px); }
    .preview .slide p, .preview .slide li, .preview .slide blockquote { font-size:clamp(12px,1.8vw,20px); }
    .preview .slide .statistic-value { font-size:clamp(32px,6vw,64px); }
    details { margin-top:12px; }
    code { color:#4a62d8; }
    """
    document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Presentation Layout Gallery</title><style>{gallery_css}</style></head>
<body data-theme="light"><main class="gallery"><h1>Presentation Layout Gallery</h1><p>Browse the available slide layouts and their input fields.</p><div class="gallery-grid">{''.join(previews)}</div></main></body></html>'''
    output = ROOT / "examples" / "index.html"
    output.write_text(document, encoding="utf-8")
    print(f"Created {output}")


if __name__ == "__main__":
    main()
