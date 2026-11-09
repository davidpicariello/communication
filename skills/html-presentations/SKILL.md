---
name: HTML Presentations
description: Create and refine HTML slide decks from JSON source files.
---

# HTML Presentation Builder

Create self-contained HTML presentations using the project's JSON-based builder code. This code uses the available templates to structure clear, concise content for the requested topic.

## How it works

The builder takes a JSON source file and generates a self-contained HTML presentation with its styles, slide content, navigation controls, and any supplied local images embedded in the output. The JSON describes the presentation title, optional theme and slide size, and an ordered list of slides. Each slide names a template layout and provides values for that layout's fields.

The generated HTML also embeds the complete source data in a non-executable `<script type="application/json">` element. Before inserting it, the builder serializes the source as JSON and replaces `<` with the JSON escape `\u003c`; this prevents values such as `</script>` from ending the element during HTML parsing. The browser can still read and parse the original JSON data, but it is not executed as JavaScript.

This embedded source makes the HTML a portable copy of both the presentation and its editable data. To revise a deck, run `python3 scripts/extract_source.py PRESENTATION.html` to write the embedded source to a randomly named JSON file. Edit that file and run `python3 scripts/create.py SOURCE.json -o PRESENTATION.html` to regenerate the deck. The extraction script prints the path it created. Keep the source JSON while you're editing and regenerating the deck. After editing is complete and you've confirmed the HTML, delete the temporary JSON; its data remains embedded in the deck and can be recovered when needed.

## Create a presentation

Install the Python dependencies with `python3 -m pip install -r requirements.txt` in a virtual environment before running the builder. YAML templates are loaded with PyYAML's safe loader; presentation source files remain JSON.

1. Create a temporary JSON source file from the user's requested presentation. It must contain `title`, optional `theme` (`light` or `dark`), optional `size` (`widescreen` or `standard`), and a non-empty `slides` array.
2. Each slide specifies a `layout` ID and a `values` object. Layout IDs, field names, and field types are listed in `examples/index.html`. Use the available layouts to structure concise content that directly addresses the user's requested topic.
3. Run `python3 scripts/create.py presentation-source.json -o presentation.html`.
4. Confirm the HTML was created successfully. Keep the temporary JSON source while making further edits; after editing is complete, delete it. Its source data is embedded in the HTML.
5. Open the generated HTML in a browser. It works offline and supports keyboard and on-screen navigation.

To revise a deck later, recover its latest source JSON into a randomly named file with `python3 scripts/extract_source.py presentation.html`. The script prints the created JSON path. Edit that JSON file and regenerate with `python3 scripts/create.py RECOVERED.json -o presentation.html`. Delete the recovered JSON after editing is complete and you've confirmed the updated HTML.

Example source:

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

## Entering content

- Fields with type `heading` or `text` take strings. Include actual `\n` newline escapes in JSON strings for line breaks.
- Fields with type `bullets` take arrays of strings, one item per bullet.
- Fields with type `image` take local image file paths. Images are embedded so the output remains portable and offline.
- Text is escaped before insertion into HTML. Do not enter HTML markup expecting it to be interpreted.
- Keep slide content brief. Text is automatically reduced to fit, but very dense slides may still be hard to read.
- Exceeding a template field limit fails deck generation. At runtime, a deck also stops with a visible error if fitted content still overflows at its minimum font size.

## Presentation controls and styling

- Use the left/right arrow keys, Page Up/Page Down, or the on-screen buttons to navigate. Home and End go to the first and last slides.
- Choose a theme (`light` or `dark`) independently from a slide size (`widescreen` 16:9 or `standard` 4:3).
- Use local image assets and system fonts; avoid external network dependencies.

## Extend the project

- Add a slide layout as one `.yaml` file in `templates/`. Use the structure of the existing templates: `name`, `description`, a `fields` list, and a multiline HTML `body: |` block. Each field specifies `name`, `label`, `type`, a boolean `required`, an `example` value, and a hard limit: `max_chars` for string fields or `max_items` and `max_item_chars` for bullet fields. Bullet examples are native YAML lists of strings. Use `{{field_name}}` placeholders in the HTML body. Templates are data loaded with `yaml.safe_load()`, not executable Python.
- Supported field types are `heading`, `text`, `bullets`, and `image`. Escape content for HTML and validate assets when adding new field behavior.
- Add theme stylesheets under `styles/themes/` and size stylesheets under `styles/sizes/`; keep shared layout rules in `styles/base.css`.
- Run `python3 scripts/gallery.py` to refresh the layout gallery.
- Run `python3 scripts/build_examples.py` to clear `examples/` except for `index.html`, then generate one example presentation per template and each size/theme combination in `examples/<size>-<theme>/` subfolders. Each subfolder's `index.html` previews the decks in scaled iframes whose viewport ratio is read from the size stylesheet. The script discovers available sizes and themes from their CSS files.
