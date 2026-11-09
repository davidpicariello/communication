---
name: HTML Presentations
description: Create and refine HTML slide decks from JSON source files.
---

# HTML Presentation Builder

Create self-contained HTML presentations using the project's JSON-based builder code. This code uses the available templates to structure clear, concise content for the requested topic.

## How it works

The builder takes a JSON source file and generates a self-contained HTML presentation with its styles, slide content, navigation controls, and any supplied local images embedded in the output. The JSON describes the presentation title, optional theme and slide size, and an ordered list of slides. Each slide names a template layout and provides values for that layout's fields.

The generated HTML also embeds the complete source data in a non-executable `<script type="application/json">` element. Before inserting it, the builder serializes the source as JSON and replaces `<` with the JSON escape `\u003c`; this prevents values such as `</script>` from ending the element during HTML parsing. The browser can still read and parse the original JSON data, but it is not executed as JavaScript.

This embedded source makes the HTML a portable copy of both the presentation and its editable data. To revise a deck, run `python3 scripts/extract_source.py PRESENTATION.html` to write the embedded source to a randomly named JSON file. Edit that file and run `python3 scripts/create.py SOURCE.json -o PRESENTATION.html` to regenerate the deck. The extraction script prints the path it created. For new decks, use a temporary JSON source file and delete it after confirming the HTML was generated successfully; the embedded data can be recovered when needed.

## Create a presentation

1. Create a temporary JSON source file from the user's requested presentation. It must contain `title`, optional `theme` (`clean` or `dark`), optional `size` (`widescreen` or `standard`), and a non-empty `slides` array.
2. Each slide specifies a `layout` ID and a `values` object. Layout IDs, field names, and field types are listed in `templates/index.html`. Use the available layouts to structure concise content that directly addresses the user's requested topic.
3. Run `python3 scripts/create.py presentation-source.json -o presentation.html`.
4. After confirming the HTML was created successfully, delete the temporary JSON source file. Its source data is embedded in the HTML.
5. Open the generated HTML in a browser. It works offline and supports keyboard and on-screen navigation.

To revise a deck later, recover its latest source JSON into a randomly named file with `python3 scripts/extract_source.py presentation.html`. The script prints the created JSON path. Edit that JSON file, regenerate with `python3 scripts/create.py RECOVERED.json -o presentation.html`, then delete the recovered JSON file after successful generation.

Example source:

```json
{
  "title": "Cats vs. Dogs",
  "theme": "clean",
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

## Presentation controls and styling

- Use the left/right arrow keys, Page Up/Page Down, or the on-screen buttons to navigate. Home and End go to the first and last slides.
- Choose a theme (`clean` or `dark`) independently from a slide size (`widescreen` 16:9 or `standard` 4:3).
- Use local image assets and system fonts; avoid external network dependencies.

## Extend the project

- Add a slide layout as one `.html` file in `templates/`. Begin it with the metadata comment used by the existing templates: `name`, `description`, and a `fields` list. Each field specifies `name`, `label`, `type`, and whether it is required. Use `{{field_name}}` placeholders in the HTML body.
- Supported field types are `heading`, `text`, `bullets`, and `image`. Escape content for HTML and validate assets when adding new field behavior.
- Add theme stylesheets under `styles/themes/` and size stylesheets under `styles/sizes/`; keep shared layout rules in `styles/base.css`.
- Run `python3 scripts/gallery.py` to refresh the layout gallery.
