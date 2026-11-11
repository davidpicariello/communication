# HTML Presentation Builder

A Python tool for creating self-contained HTML slide decks from JSON source files and YAML layout templates. Template loading uses PyYAML's safe loader; generated decks need no dependencies.

## Quick start

### Set up Python

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r skills/html-presentations/requirements.txt
```

### Create presentation

Create a JSON source file containing a title, optional theme and size, and slides identified by layout name and field values.

```json
{
  "title": "Cats vs. Dogs",
  "theme": "light",
  "size": "widescreen",
  "slides": [
    {
      "layout": "title",
      "values": {
        "title": "Cats vs. Dogs",
        "subtitle": "Two beloved companions",
        "presenter": "A quick comparison"
      }
    }
  ]
}
```

From the repository root, generate the deck with `python3 skills/html-presentations/scripts/create.py presentation.json -o presentation.html`. Layout names and fields are listed in `skills/html-presentations/examples/index.html`. Bullet fields take arrays of strings; image fields take local image paths relative to the repository root, which are embedded into the finished deck. Shared image assets live in the root `assets/` directory.

### Making edits

The generated HTML embeds the source JSON and image data in a non-executable `application/json` script element so decks can be edited and regenerated later. Keep the JSON source while you're editing and regenerating the deck. Delete the temporary JSON after editing is complete and you've confirmed the HTML; the embedded source can be recovered later with `skills/html-presentations/scripts/extract_source.py` if you need to revise the deck again.

Template field limits are hard validation checks: the builder rejects strings over `max_chars`, or bullet lists over `max_items` / `max_item_chars`. At runtime, the deck also stops with a visible error if content still overflows after shrinking to its minimum font size. The layout gallery shows each field's limits.

To restore the embedded JSON for later edits, run `python3 skills/html-presentations/scripts/extract_source.py presentation.html`. The script prints the path to the randomly named JSON file it creates. It restores embedded images as data URIs, so regenerating the deck does not require the original image files. Edit the file and regenerate the presentation with `skills/html-presentations/scripts/create.py`; delete the extracted temporary JSON after editing is complete and you've confirmed the updated HTML.

Generated decks work offline and include keyboard navigation. Use the arrow keys, Page Up/Page Down, Home, or End to navigate.

## Layout gallery

Generate or refresh the local gallery with:

```sh
python3 skills/html-presentations/scripts/gallery.py
```

Open `skills/html-presentations/examples/index.html` in a browser to see the available layouts and their fields. Running `skills/html-presentations/scripts/build_examples.py` replaces this page with title-slide previews for each size/theme variant.

## Example decks

Each template field includes an example value. Running this command clears `skills/html-presentations/examples/` except for `index.html`, then generates self-contained HTML decks for every template and size/theme combination:

```sh
python3 skills/html-presentations/scripts/build_examples.py
```

The generated decks are saved in `skills/html-presentations/examples/<size>-<theme>/` folders. The script discovers sizes and themes from the CSS files in `skills/html-presentations/styles/sizes/` and `skills/html-presentations/styles/themes/`; there are currently four combinations. Each folder contains an `index.html` with scaled iframe previews plus one deck per template, named by its layout ID. The root `skills/html-presentations/examples/index.html` shows a scaled preview of each variant's title slide and links to that folder's “Show all slides” index.

## Project structure

- `skills/html-presentations/templates/` — one YAML file per slide layout, with metadata and a multiline HTML `body`.
- `skills/html-presentations/examples/` — generated layout gallery and sample decks grouped by size and theme.
- `assets/` — shared repository-level source images used by template examples and other skills.
- `skills/html-presentations/styles/` — shared CSS, themes, and slide sizes.
- `skills/html-presentations/scripts/create.py` — JSON-driven deck generator.
- `skills/html-presentations/scripts/field_types/` — validation and rendering handlers for each field type.
- `skills/html-presentations/scripts/extract_source.py` — extracts embedded source JSON to a random filename for editing.
- `skills/html-presentations/scripts/gallery.py` — offline template gallery generator.
- `skills/html-presentations/scripts/build_examples.py` — builds one example deck for each template.
- `skills/html-presentations/SKILL.md` — shared agent instructions.
- `.opencode/skills/html-presentations/SKILL.md` — OpenCode entry point referencing the shared skill.
