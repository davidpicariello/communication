#!/usr/bin/env python3
"""Extract embedded presentation JSON into a randomly named source file."""

from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
from pathlib import Path

SOURCE_PATTERN = re.compile(
    r'<script\s+type="application/json"\s+id="presentation-source">(.*?)</script\s*>',
    re.DOTALL,
)


def extract_source(html_path: Path, output_dir: Path) -> Path:
    """Extract the embedded JSON and write it to a collision-safe random path."""
    html_text = html_path.read_text(encoding="utf-8")
    match = SOURCE_PATTERN.search(html_text)
    if not match:
        raise ValueError(f"No embedded presentation source found in {html_path}")
    source = json.loads(match.group(1))
    if not isinstance(source, dict):
        raise ValueError(f"Embedded presentation source in {html_path} must be an object")

    # The generated deck carries image bytes alongside the original editable paths.
    # Restore image fields as data URIs so the extracted JSON works without those files.
    embedded_images = source.pop("_embedded_images", [])
    if not isinstance(embedded_images, list):
        raise ValueError("Embedded image data must be an array")
    slides = source.get("slides")
    if not isinstance(slides, list):
        raise ValueError("Embedded presentation source has no valid slides array")
    for image in embedded_images:
        if not isinstance(image, dict):
            raise ValueError("Embedded image entry must be an object")
        slide_index = image.get("slide")
        field_name = image.get("field")
        data_uri = image.get("data_uri")
        if (
            not isinstance(slide_index, int)
            or isinstance(slide_index, bool)
            or not 0 <= slide_index < len(slides)
            or not isinstance(field_name, str)
            or not isinstance(data_uri, str)
        ):
            raise ValueError("Embedded image entry has invalid slide, field, or image data")
        slide = slides[slide_index]
        if not isinstance(slide, dict) or not isinstance(slide.get("values"), dict):
            raise ValueError(f"Embedded image references invalid slide {slide_index + 1}")
        slide["values"][field_name] = data_uri

    output_dir.mkdir(parents=True, exist_ok=True)
    while True:
        output_path = output_dir / f"presentation-source-{secrets.token_hex(6)}.json"
        try:
            with output_path.open("x", encoding="utf-8") as output_file:
                json.dump(source, output_file, ensure_ascii=False, indent=2)
                output_file.write("\n")
            return output_path
        except FileExistsError:
            continue


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract embedded JSON source from a generated presentation.")
    parser.add_argument("presentation", type=Path, help="generated presentation HTML file")
    parser.add_argument("-d", "--directory", type=Path, help="directory for the extracted JSON (defaults to the current directory)")
    args = parser.parse_args()
    try:
        output_path = extract_source(args.presentation.expanduser(), (args.directory or Path.cwd()).expanduser())
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Could not extract presentation source: {error}", file=sys.stderr)
        return 1
    print(output_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
