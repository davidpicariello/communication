import importlib.util
import json
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("presentation_builder", ROOT / "scripts" / "create.py")
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BuilderTests(unittest.TestCase):
    def example_source(self):
        return {
            "title": "Sample deck",
            "theme": "light",
            "size": "widescreen",
            "slides": [
                {
                    "layout": "title",
                    "values": {"title": "Hello", "subtitle": "A sample", "presenter": ""},
                },
                {
                    "layout": "comparison",
                    "values": {
                        "title": "Compare",
                        "left_heading": "One",
                        "left_bullets": ["First", "Second"],
                        "right_heading": "Two",
                        "right_bullets": ["Third", "Fourth"],
                    },
                },
            ],
        }

    def test_all_templates_have_metadata_and_render(self):
        templates = builder.templates()
        self.assertEqual(len(templates), 10)
        self.assertTrue({"agenda", "timeline", "statistic"}.issubset({item["id"] for item in templates}))
        for template in templates:
            values = {}
            for field in template["fields"]:
                field_type = field.get("type")
                values[field["name"]] = ["First", "Second"] if field_type == "bullets" else "" if field_type == "image" else "Example"
            self.assertNotIn("{{", builder.render_slide(template, values))

    def test_theme_and_size_names_come_from_stylesheets(self):
        self.assertEqual(builder.THEMES, {path.stem for path in (builder.STYLE_DIR / "themes").glob("*.css")})
        self.assertEqual(builder.SIZES, {path.stem for path in (builder.STYLE_DIR / "sizes").glob("*.css")})

    def test_all_template_fields_have_examples(self):
        for template in builder.templates():
            for field in template["fields"]:
                with self.subTest(template=template["id"], field=field["name"]):
                    self.assertTrue(field.get("example"))
                    if field.get("type") == "bullets":
                        self.assertIn("max_items", field)
                        self.assertIn("max_item_chars", field)
                        example = field["example"]
                        self.assertIsInstance(example, list)
                        self.assertTrue(all(isinstance(item, str) for item in example))
                    elif field.get("type") == "image":
                        self.assertIn("max_chars", field)
                        self.assertTrue((ROOT / field["example"]).is_file())
                    else:
                        self.assertIn("max_chars", field)

        timeline = next(item for item in builder.templates() if item["id"] == "timeline")
        milestones = next(field for field in timeline["fields"] if field["name"] == "milestones")
        self.assertLessEqual(len(milestones["example"]), int(milestones["max_items"]))

    def test_yaml_templates_preserve_native_values_and_multiline_markup(self):
        template = builder.read_template(ROOT / "templates" / "title.yaml")
        self.assertEqual(template["id"], "title")
        subtitle = next(field for field in template["fields"] if field["name"] == "subtitle")
        self.assertIs(subtitle["required"], False)
        self.assertIsInstance(subtitle["max_chars"], int)
        self.assertIn('<div class="title-slide">\n  <p', template["body"])
        self.assertFalse(list((ROOT / "templates").glob("*.html")))

    def test_yaml_loader_rejects_unsafe_tags_and_invalid_templates(self):
        cases = [
            ("!!python/object/apply:builtins.str [unsafe]", "invalid YAML"),
            ("name: [", "invalid YAML"),
            ("- not a template", "template must be a mapping"),
            ("name: Example\ndescription: Example\nfields: []", "'body'"),
            ("name: Example\ndescription: Example\nbody: <div></div>\nfields: {}", "'fields'"),
            (
                'name: Example\ndescription: Example\nbody: <div></div>\n'
                'fields: [{name: title, required: "false"}]',
                "boolean 'required'",
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.yaml"
            for content, message in cases:
                with self.subTest(content=content):
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, message):
                        builder.read_template(path)

    def test_example_builders_use_yaml_bullet_arrays_and_optional_flags(self):
        examples = runpy.run_path(str(ROOT / "scripts" / "build_examples.py"), run_name="build_examples_test")
        gallery = runpy.run_path(str(ROOT / "scripts" / "gallery.py"), run_name="gallery_test")
        for template in builder.templates():
            source = examples["source_for_template"](template, "light", "widescreen")
            builder.render_source(source)
            for field in template["fields"]:
                if field.get("type") == "bullets":
                    self.assertEqual(gallery["example_text"](field), " · ".join(field["example"]))
                if field.get("required") is False:
                    self.assertIn("optional", gallery["field_details"](field))

    def test_example_cleanup_preserves_only_gallery_index(self):
        namespace = runpy.run_path(str(ROOT / "scripts" / "build_examples.py"), run_name="build_examples_test")
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "examples"
            (output_dir / "old-variant").mkdir(parents=True)
            (output_dir / "index.html").write_text("gallery", encoding="utf-8")
            (output_dir / "old.html").write_text("old output", encoding="utf-8")
            (output_dir / "old-variant" / "old.html").write_text("old output", encoding="utf-8")

            namespace["clear_examples"](output_dir)

            self.assertEqual([path.name for path in output_dir.iterdir()], ["index.html"])
            self.assertEqual((output_dir / "index.html").read_text(encoding="utf-8"), "gallery")

    def test_variant_index_iframes_use_size_stylesheet_ratio(self):
        namespace = runpy.run_path(str(ROOT / "scripts" / "build_examples.py"), run_name="build_examples_test")
        with tempfile.TemporaryDirectory() as directory:
            variant_dir = Path(directory)
            namespace["build_variant_index"](
                variant_dir,
                builder.templates(),
                "light",
                "standard",
                ROOT / "styles" / "sizes" / "standard.css",
            )
            index = (variant_dir / "index.html").read_text(encoding="utf-8")

        self.assertEqual(index.count("<iframe "), 10)
        self.assertIn("display:flex; flex-flow:row wrap; gap:24px; max-width:calc(100vw - 72px)", index)
        self.assertIn('width="1280" height="960"', index)
        self.assertIn("width:552px", index)
        self.assertIn("transform:scale(0.431250)", index)

    def test_root_index_previews_each_variant_title_slide_once(self):
        namespace = runpy.run_path(str(ROOT / "scripts" / "build_examples.py"), run_name="build_examples_test")
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            index_path = output_dir / "index.html"
            index_path.write_text(
                '<html><head><style></style></head><body><main class="gallery">'
                '<div class="gallery-grid"></div></main></body></html>',
                encoding="utf-8",
            )
            variants = [
                ("standard", "light", ROOT / "styles" / "sizes" / "standard.css"),
                ("widescreen", "dark", ROOT / "styles" / "sizes" / "widescreen.css"),
            ]

            namespace["build_root_index"](output_dir, variants)
            namespace["build_root_index"](output_dir, variants)
            index = index_path.read_text(encoding="utf-8")

        self.assertEqual(index.count("<iframe "), 2)
        self.assertIn('src="standard-light/title.html"', index)
        self.assertIn('src="widescreen-dark/title.html"', index)
        self.assertIn('href="standard-light/index.html">Show all slides</a>', index)
        self.assertNotIn("gallery-grid", index)
        self.assertNotIn("Open title slide", index)

    def test_user_text_is_escaped_and_line_breaks_render(self):
        template = next(item for item in builder.templates() if item["id"] == "title")
        rendered = builder.render_slide(template, {"title": "<script>", "subtitle": "one\ntwo", "presenter": ""})
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("one<br>two", rendered)
        self.assertNotIn("<script>", rendered)

    def test_bullet_content_is_escaped(self):
        template = next(item for item in builder.templates() if item["id"] == "text-bullets")
        rendered = builder.render_slide(template, {"title": "Notes", "intro": "", "bullets": ["<bad>", "Good"]})
        self.assertIn("<li>&lt;bad&gt;</li>", rendered)
        self.assertIn("<li>Good</li>", rendered)

    def test_source_is_embedded_as_safe_round_trip_json(self):
        source = self.example_source()
        source["slides"][0]["values"]["subtitle"] = "</script><img src=x onerror=alert(1)> & \"quotes\""
        deck = builder.render_source(source)
        self.assertIn('<script type="application/json" id="presentation-source">', deck)
        self.assertNotIn("</script><img", deck)
        embedded = deck.split('<script type="application/json" id="presentation-source">', 1)[1].split("</script>", 1)[0]
        self.assertEqual(json.loads(embedded), source)

    def test_validation_rejects_unknown_fields_and_invalid_bullets(self):
        source = self.example_source()
        source["slides"][0]["values"]["extra"] = "Nope"
        with self.assertRaisesRegex(ValueError, "unknown field"):
            builder.validate_source(source)
        source = self.example_source()
        source["slides"][1]["values"]["left_bullets"] = "not an array"
        with self.assertRaisesRegex(ValueError, "array of strings"):
            builder.validate_source(source)

    def test_rendering_hard_fails_when_template_limits_are_exceeded(self):
        source = self.example_source()
        title_template = next(item for item in builder.templates() if item["id"] == "title")
        title_limit = next(int(field["max_chars"]) for field in title_template["fields"] if field["name"] == "title")
        source["slides"][0]["values"]["title"] = "x" * (title_limit + 1)
        with self.assertRaisesRegex(ValueError, f"field 'title'.*maximum is {title_limit}"):
            builder.render_source(source)

        source = self.example_source()
        comparison = next(item for item in builder.templates() if item["id"] == "comparison")
        left_bullets = next(field for field in comparison["fields"] if field["name"] == "left_bullets")
        item_limit = int(left_bullets["max_items"])
        source["slides"][1]["values"]["left_bullets"] = ["Point"] * (item_limit + 1)
        with self.assertRaisesRegex(
            ValueError, f"field 'left_bullets' has {item_limit + 1} items; maximum is {item_limit}"
        ):
            builder.render_source(source)

        source = self.example_source()
        char_limit = int(left_bullets["max_item_chars"])
        source["slides"][1]["values"]["left_bullets"] = ["x" * (char_limit + 1)]
        with self.assertRaisesRegex(
            ValueError, f"left_bullets' item 1 has {char_limit + 1} characters; maximum is {char_limit}"
        ):
            builder.render_source(source)

    def test_generated_deck_uses_fixed_font_sizes_without_runtime_overflow_checks(self):
        deck = builder.render_source(self.example_source())
        self.assertNotIn("data-fit", deck)
        self.assertNotIn("data-max-size", deck)
        self.assertNotIn("data-min-size", deck)
        self.assertNotIn("fitText", deck)
        self.assertNotIn("failRender", deck)
        self.assertNotIn("render-error", deck)
        self.assertIn('id="slide-picker"', deck)
        self.assertIn("const choices = slides.map", deck)
        self.assertIn("if (event.target.closest('button')) return;", deck)
        self.assertIn("addEventListener('keydown'", deck)

    def test_source_requires_title_and_slides(self):
        with self.assertRaisesRegex(ValueError, "title"):
            builder.validate_source({"slides": []})
        with self.assertRaisesRegex(ValueError, "non-empty array"):
            builder.validate_source({"title": "Empty", "slides": []})

    def test_cli_generates_html_from_json(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "deck.json"
            output_path = Path(directory) / "custom.html"
            source_path.write_text(json.dumps(self.example_source()), encoding="utf-8")
            with mock.patch("sys.argv", ["create.py", str(source_path), "--output", str(output_path)]):
                self.assertEqual(builder.main(), 0)
            self.assertIn('id="presentation-source"', output_path.read_text(encoding="utf-8"))

    def test_extract_source_writes_random_json_that_round_trips(self):
        source = self.example_source()
        source["slides"][0]["values"]["subtitle"] = "Closing tag </script> stays data"
        deck = builder.render_source(source)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html_path = root / "deck.html"
            html_path.write_text(deck, encoding="utf-8")
            namespace = runpy.run_path(str(ROOT / "scripts" / "extract_source.py"), run_name="extract_source_test")
            extracted_path = namespace["extract_source"](html_path, root / "sources")
            self.assertRegex(extracted_path.name, r"^presentation-source-[0-9a-f]{12}\.json$")
            self.assertEqual(json.loads(extracted_path.read_text(encoding="utf-8")), source)

    def test_extract_source_errors_when_embedded_source_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            html_path = Path(directory) / "legacy.html"
            html_path.write_text("<html><body>No source</body></html>", encoding="utf-8")
            namespace = runpy.run_path(str(ROOT / "scripts" / "extract_source.py"), run_name="extract_source_test")
            with self.assertRaisesRegex(ValueError, "No embedded presentation source"):
                namespace["extract_source"](html_path, Path(directory))


if __name__ == "__main__":
    unittest.main()
