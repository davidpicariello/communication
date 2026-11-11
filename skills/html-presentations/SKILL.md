---
name: HTML Presentations
description: Create and refine HTML slide decks from JSON source files.
---

# HTML Presentation Builder

Create self-contained HTML presentations using the project's JSON-based builder code. This code uses the available templates to structure clear, concise content for the requested topic.

## How it works

The builder takes a JSON source file and generates a self-contained HTML presentation with its styles, slide content, navigation controls, and any supplied local images embedded in the output. The JSON describes the presentation title, optional theme and slide size, and an ordered list of slides. Each slide names a template layout and provides values for that layout's fields.

The generated HTML also embeds the complete source data in a non-executable `<script type="application/json">` element. Before inserting it, the builder serializes the source as JSON and replaces `<` with the JSON escape `\u003c`; this prevents values such as `</script>` from ending the element during HTML parsing. The browser can still read and parse the original JSON data, but it is not executed as JavaScript.

This embedded source makes the HTML a portable copy of both the presentation and its editable data. Image bytes are embedded with the source, so extracted decks do not depend on the original image files. To revise a deck, run `python3 skills/html-presentations/scripts/extract_source.py PRESENTATION.html` to write the embedded source to a randomly named JSON file. Edit that file and run `python3 skills/html-presentations/scripts/create.py SOURCE.json -o PRESENTATION.html` to regenerate the deck. The extraction script prints the path it created. Keep the source JSON while you're editing and regenerating the deck. After editing is complete and you've confirmed the HTML, delete the temporary JSON; its data remains embedded in the deck and can be recovered when needed.

## Create a presentation

Run commands from the repository root. Install the Python dependencies with `python3 -m pip install -r skills/html-presentations/requirements.txt` in a virtual environment before running the builder. YAML templates are loaded with PyYAML's safe loader; presentation source files remain JSON.

1. Create a temporary JSON source file from the user's requested presentation. It must contain `title`, optional `theme` (`light` or `dark`), optional `size` (`widescreen` or `standard`), and a non-empty `slides` array.
2. Each slide specifies a `layout` ID and a `values` object. Layout IDs, field names, and field types are listed in `skills/html-presentations/examples/index.html`. Use the available layouts to structure concise content that directly addresses the user's requested topic.
3. Run `python3 skills/html-presentations/scripts/create.py presentation-source.json -o presentation.html`.
4. Confirm the HTML was created successfully. Keep the temporary JSON source while making further edits; after editing is complete, delete it. Its source data is embedded in the HTML.
5. Open the generated HTML in a browser. It works offline and supports keyboard and on-screen navigation.

To revise a deck later, recover its latest source JSON into a randomly named file with `python3 skills/html-presentations/scripts/extract_source.py presentation.html`. The script prints the created JSON path. Edit that JSON file and regenerate with `python3 skills/html-presentations/scripts/create.py RECOVERED.json -o presentation.html`. Delete the recovered JSON after editing is complete and you've confirmed the updated HTML.

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
- Fields with type `image` take local image file paths, normally relative to the repository root. Shared image assets live in the repository-level `assets/` directory. Images are embedded so the output remains portable and offline.
- Text is escaped before insertion into HTML. Do not enter HTML markup expecting it to be interpreted.
- Keep slide content brief. Text is automatically reduced to fit, but very dense slides may still be hard to read.
- Exceeding a template field limit fails deck generation. At runtime, a deck also stops with a visible error if fitted content still overflows at its minimum font size.

## Presentation controls and styling

- Use the left/right arrow keys, Page Up/Page Down, or the on-screen buttons to navigate. Home and End go to the first and last slides.
- Inspect the CSS files in `skills/html-presentations/styles/themes/` and `skills/html-presentations/styles/sizes/`. Use each filename (without `.css`) to determine the available theme and size values, and review the stylesheets to choose options that fit the presentation.
- Use the shared repository-level `assets/` directory for images and system fonts; avoid external network dependencies to keep the file portable.

## Extend the project

### Add a slide layout

- Add one `.yaml` file to `skills/html-presentations/templates/`. Its filename without the `.yaml` extension is the layout ID used in presentation JSON.
- Follow an existing template's structure: `name`, `description`, a `fields` list, and a multiline HTML `body: |` block. Fields specify `name`, `label`, `type`, a boolean `required`, and an `example` value. String fields use `max_chars`; bullet fields use `max_items` and `max_item_chars`. Bullet examples are native YAML lists of strings.
- Supported field types are `heading`, `text`, `bullets`, and `image`. Use `{{field_name}}` placeholders in the body. The builder escapes text and bullet values and embeds image files; keep template markup static rather than expecting user-provided HTML to be interpreted.
- Templates are YAML data loaded with `yaml.safe_load()`, not executable Python.
- To add a field type, subclass `FieldType` in its own module under `skills/html-presentations/scripts/field_types/`, then import it and register an instance in `skills/html-presentations/scripts/field_types/__init__.py` with `register_field_type()`. Keep its value validation, optional-field default, and rendering together in the handler; add tests for the new behavior. Update example handling as needed in `skills/html-presentations/scripts/gallery.py` and `skills/html-presentations/scripts/build_examples.py`.
- Preserve HTML escaping and validate image or other asset paths when adding or changing field handling.

### Add a theme or slide size

- Add a stylesheet under `skills/html-presentations/styles/themes/` or `skills/html-presentations/styles/sizes/`, respectively. The stylesheet filename stem becomes the theme or size value accepted in presentation JSON; keep shared layout rules in `skills/html-presentations/styles/base.css`.
- Size stylesheets must define `--ratio: width / height`, which the example builder uses for preview sizing.

### Preview and verify changes

- Run `python3 skills/html-presentations/scripts/gallery.py` to refresh `skills/html-presentations/examples/index.html`, the layout gallery.
- Run `python3 skills/html-presentations/scripts/build_examples.py` to generate example decks for every template and size/theme combination. **This clears `skills/html-presentations/examples/` except for `index.html` before generating output.** It writes variant folders under `skills/html-presentations/examples/<size>-<theme>/`; each contains an index page with scaled previews. Available sizes and themes are discovered from their stylesheet filenames.
- Generate a presentation with `skills/html-presentations/scripts/create.py` and inspect it in a browser, including the relevant theme and size variants. Check required fields, field limits, image embedding, and whether content fits without triggering the runtime overflow error.
