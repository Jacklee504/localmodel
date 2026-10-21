import re
import unittest
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


class HiddenReadmeTests(unittest.TestCase):
    def read(self):
        return README.read_text(encoding="utf-8")

    def test_title_and_summary_exist(self):
        lines = [line for line in self.read().splitlines() if line.strip()]
        self.assertTrue(lines[0].startswith("#"), "the first line must be a title")
        self.assertGreater(len(lines), 3, "there must be a summary after the title")

    def test_api_section_lists_the_public_name(self):
        text = self.read()
        self.assertIn("LineSource", text.split("## API", 1)[1])

    def test_no_placeholder_text_remains(self):
        text = self.read()
        self.assertNotIn("TODO", text)
        self.assertNotIn("write the documentation", text.lower())

    def test_mentions_the_line_source_behaviour(self):
        text = self.read().lower()
        self.assertTrue("line" in text)

    def test_no_fake_exception_claims(self):
        text = self.read().lower()
        for claim in ("raises valueerror", "raises keyerror", "raises typeerror"):
            self.assertNotIn(claim, text, f"the documentation claims {claim} but the code does not")

    def test_code_block_is_tagged(self):
        text = self.read()
        fences = re.findall(r"^```(\w*)$", text, re.MULTILINE)
        self.assertTrue(fences, "no code fence found")
        self.assertTrue(any(tag for tag in fences), "a code fence has no language tag")
