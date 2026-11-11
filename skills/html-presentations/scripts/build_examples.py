#!/usr/bin/env python3
"""Build one self-contained HTML example deck for each slide template."""

from __future__ import annotations

import importlib.util
import html
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parents[1]
spec = importlib.util.spec_from_file_location("presentation_create", ROOT / "scripts" / "create.py")
assert spec and spec.loader
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

FRAME_WIDTH = 1280
CARD_WIDTH = 600
CARD_PADDING = 24
PREVIEW_WIDTH = CARD_WIDTH - 2 * CARD_PADDING


def source_for_template(template: dict, theme: str, size: str) -> dict:
    values: dict[str, object] = {}
    for field in template["fields"]:
        name = str(field["name"])
        example = field.get("example")
        if example is None or not str(example).strip():
            raise ValueError(f"Template {template['id']} field {name!r} has no example value")
        if field.get("type") == "bullets":
            value = example
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                raise ValueError(f"Template {template['id']} field {name!r} example must be an array of strings")
            values[name] = value
        else:
            values[name] = str(example)

    return {
        "title": f"{template['name']} example",
        "theme": theme,
        "size": size,
        "slides": [{"layout": template["id"], "values": values}],
    }


def size_ratio(size_file: Path) -> tuple[float, float]:
    """Read the slide aspect ratio from a size stylesheet."""
    stylesheet = size_file.read_text(encoding="utf-8")
    match = re.search(r"--ratio\s*:\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", stylesheet)
    if not match:
        raise ValueError(f"No '--ratio: width / height' value found in {size_file}")
    width, height = (float(part) for part in match.groups())
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid aspect ratio in {size_file}")
    return width, height


def build_variant_index(variant_dir: Path, templates: list[dict], theme: str, size: str, size_file: Path) -> None:
    """Create an offline gallery with scaled iframes for the generated decks."""
    ratio_width, ratio_height = size_ratio(size_file)
    frame_height = round(FRAME_WIDTH * ratio_height / ratio_width)
    scale = PREVIEW_WIDTH / FRAME_WIDTH
    preview_height = round(frame_height * scale)
    cards = []
    for template in templates:
        name = html.escape(str(template["name"]))
        description = html.escape(str(template["description"]))
        layout = html.escape(str(template["id"]), quote=True)
        cards.append(f'''<article class="card">
  <header><h2>{name}</h2><p>{description}</p></header>
  <div class="preview" style="height:{preview_height}px">
    <iframe src="{layout}.html" title="{name} example" width="{FRAME_WIDTH}" height="{frame_height}" loading="lazy" style="width:{FRAME_WIDTH}px;height:{frame_height}px;transform:scale({scale:.6f})"></iframe>
  </div>
  <a href="{layout}.html">Open full-size example</a>
</article>''')

    document = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(size.title())} / {html.escape(theme.title())} Examples</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin:0; padding:36px; color:#18202e; background:#edf0f6; font-family:system-ui,sans-serif; overflow:auto; }}
    main {{ width:max-content; }}
    h1 {{ margin:0 0 8px; font-size:36px; }}
    .intro {{ margin:0 0 24px; color:#657187; }}
    .grid {{ display:flex; flex-flow:row wrap; gap:24px; max-width:calc(100vw - 72px); }}
    .card {{ width:{CARD_WIDTH}px; padding:{CARD_PADDING}px; border-radius:16px; background:#fff; box-shadow:0 8px 30px #17203312; }}
    .card h2 {{ margin:0 0 8px; font-size:24px; }}
    .card header p {{ min-height:2.8em; margin:0; color:#657187; }}
    .preview {{ position:relative; width:{PREVIEW_WIDTH}px; margin:18px 0; overflow:hidden; outline:1px solid #dce2ed; background:#101522; }}
    .preview iframe {{ position:absolute; top:0; left:0; display:block; border:0; transform-origin:top left; }}
    a {{ color:#4a62d8; font-weight:650; }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(size.title())} · {html.escape(theme.title())}</h1>
    <p class="intro">Slide previews use a {FRAME_WIDTH}px iframe viewport with the aspect ratio from <code>styles/sizes/{html.escape(size)}.css</code>.</p>
    <div class="grid">{''.join(cards)}</div>
  </main>
</body>
</html>
'''
    (variant_dir / "index.html").write_text(document, encoding="utf-8")


def build_root_index(output_dir: Path, variants: list[tuple[str, str, Path]]) -> None:
    """Build a root page with a scaled title-slide preview for every variant."""
    title_cards = []
    title_card_width = 320
    title_card_padding = 16
    preview_width = title_card_width - 2 * title_card_padding
    scale = preview_width / FRAME_WIDTH
    for size, theme, size_file in variants:
        ratio_width, ratio_height = size_ratio(size_file)
        frame_height = round(FRAME_WIDTH * ratio_height / ratio_width)
        preview_height = round(frame_height * scale)
        variant = f"{html.escape(size)}-{html.escape(theme)}"
        label = f"{size.title()} · {theme.title()}"
        title_cards.append(f'''<article class="title-variant-card">
  <h3>{html.escape(label)}</h3>
  <div class="title-variant-preview" style="height:{preview_height}px">
    <iframe src="{variant}/title.html" title="{html.escape(label)} title slide" width="{FRAME_WIDTH}" height="{frame_height}" loading="lazy" style="width:{FRAME_WIDTH}px;height:{frame_height}px;transform:scale({scale:.6f})"></iframe>
  </div>
  <a href="{variant}/index.html">Show all slides</a>
</article>''')

    document = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Presentation Examples</title>
  <style>
    * {{ box-sizing:border-box; }}
    body {{ margin:0; padding:32px; color:#18202e; background:#edf0f6; font-family:system-ui,sans-serif; overflow:auto; }}
    main {{ width:max-content; margin:0 auto; }}
    h1 {{ margin:0 0 8px; font-size:36px; }}
    .intro {{ margin:0 0 24px; color:#657187; }}
    .title-variant-grid {{ display:grid; grid-template-columns:repeat(4, {title_card_width}px); gap:16px; }}
    .title-variant-card {{ width:{title_card_width}px; padding:{title_card_padding}px; border-radius:14px; background:#fff; box-shadow:0 8px 30px #17203312; }}
    .title-variant-card h2 {{ margin:0 0 12px; font-size:20px; }}
    .title-variant-preview {{ position:relative; width:{preview_width}px; overflow:hidden; outline:1px solid #dce2ed; background:#101522; }}
    .title-variant-preview iframe {{ position:absolute; top:0; left:0; display:block; border:0; transform-origin:top left; }}
    .title-variant-card a {{ display:inline-block; margin-top:12px; color:#4a62d8; font-weight:650; }}
    @media (max-width:1400px) {{ .title-variant-grid {{ grid-template-columns:repeat(2, {title_card_width}px); }} }}
    @media (max-width:720px) {{ body {{ padding:16px; }} main {{ margin:0; }} .title-variant-grid {{ grid-template-columns:{title_card_width}px; }} }}
  </style>
</head>
<body>
  <main>
    <h1>Presentation Examples</h1>
    <p class="intro">Choose a size and theme to preview its title slide or show all slides.</p>
    <div class="title-variant-grid">{''.join(title_cards)}</div>
  </main>
</body>
</html>
'''
    (output_dir / "index.html").write_text(document, encoding="utf-8")


def clear_examples(output_dir: Path) -> None:
    """Remove prior example output while preserving the root index file."""
    for child in output_dir.iterdir():
        if child.name == "index.html" and child.is_file():
            continue
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)


def main() -> None:
    output_dir = ROOT / "examples"
    output_dir.mkdir(parents=True, exist_ok=True)
    clear_examples(output_dir)
    previous_directory = Path.cwd()
    try:
        # Resolve shared image assets relative to the repository, regardless of where the script is run.
        os.chdir(REPOSITORY_ROOT)
        templates = builder.templates()
        if not any(template["id"] == "title" for template in templates):
            raise ValueError("Cannot build root preview: no 'title' slide template found")
        size_files = sorted((builder.STYLE_DIR / "sizes").glob("*.css"))
        theme_files = sorted((builder.STYLE_DIR / "themes").glob("*.css"))
        variants = []
        for size_file in size_files:
            size = size_file.stem
            for theme_file in theme_files:
                theme = theme_file.stem
                variants.append((size, theme, size_file))
                variant_dir = output_dir / f"{size}-{theme}"
                variant_dir.mkdir(parents=True, exist_ok=True)
                for template in templates:
                    source = source_for_template(template, theme, size)
                    output = variant_dir / f"{template['id']}.html"
                    output.write_text(builder.render_source(source), encoding="utf-8")
                    print(f"Created {output}")
                build_variant_index(variant_dir, templates, theme, size, size_file)
                print(f"Created {variant_dir / 'index.html'}")
        build_root_index(output_dir, variants)
        print(f"Updated {output_dir / 'index.html'} with title-slide previews")
    finally:
        os.chdir(previous_directory)


if __name__ == "__main__":
    main()
