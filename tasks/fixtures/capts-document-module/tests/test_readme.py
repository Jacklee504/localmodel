import re
import unittest
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


class ReadmeTests(unittest.TestCase):
    def read(self):
        self.assertTrue(README.is_file(), "README.md is missing")
        return README.read_text(encoding="utf-8")

    def test_required_sections(self):
        text = self.read()
        for heading in ("## Usage", "## Behaviour", "## Caveats", "## API"):
            self.assertIn(heading, text, f"missing section {heading}")

    def test_no_todo(self):
        self.assertNotIn("TODO", self.read())

    def test_under_sixty_lines(self):
        self.assertLessEqual(len(self.read().splitlines()), 60)

    def test_usage_has_a_fenced_example(self):
        text = self.read()
        blocks = re.findall(r"```[a-zA-Z0-9_+-]*\n(.*?)```", text, re.DOTALL)
        self.assertTrue(blocks, "no fenced code block found")
        self.assertTrue(any("LineSource" in block for block in blocks))

    def test_behaviour_documents_every_public_method(self):
        text = self.read()
        behaviour = text.split("## Behaviour", 1)[1]
        for method in ("next_line", "remaining", "peek"):
            self.assertIn(method, behaviour, f"{method} is not documented")

    def test_caveats_state_the_real_behaviours(self):
        text = self.read()
        caveats = text.split("## Caveats", 1)[1].lower()
        self.assertIn("peek", caveats)
        self.assertTrue(
            "does not advance" in caveats
            or "without consuming" in caveats
            or "same line" in caveats,
            "the peek caveat is not stated",
        )
        self.assertIn("none", caveats)
