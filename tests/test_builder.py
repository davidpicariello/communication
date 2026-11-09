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
            "theme": "clean",
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
        self.assertEqual(len(templates), 8)
        for template in templates:
            values = {}
            for field in template["fields"]:
                field_type = field.get("type")
                values[field["name"]] = ["First", "Second"] if field_type == "bullets" else "" if field_type == "image" else "Example"
            self.assertNotIn("{{", builder.render_slide(template, values))

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
