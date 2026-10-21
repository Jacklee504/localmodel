"""Reader-side helpers for a streaming line source."""


class LineSource:
    """A source of named lines that can be read once."""

    def __init__(self, lines):
        self._lines = list(lines)
        self._index = 0

    def next_line(self):
        """Return the next line, or None when the source is exhausted."""
        if self._index >= len(self._lines):
            return None
        line = self._lines[self._index]
        self._index += 1
        return line

    def remaining(self):
        """Return how many lines have not been read yet."""
        return len(self._lines) - self._index

    def peek(self):
        """Return the next line without consuming it, or None at the end."""
        if self._index >= len(self._lines):
            return None
        return self._lines[self._index]
