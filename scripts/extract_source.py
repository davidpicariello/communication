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
