# Documentation task

Write `README.md` for the module in this directory.

## What the documentation must contain

1. A title and a one-sentence summary of what the module does.
2. A section headed `## Usage` showing the shortest example that constructs a `LineSource`
   and reads a line from it.
3. A section headed `## Behaviour` that documents every public method of `LineSource`:
   `next_line`, `remaining`, and `peek`. For each one, state what it returns, and state
   what it does not do.
4. A section headed `## Caveats` that documents at least these two facts about the
   implementation:
   - `peek` does not advance the read position, so calling it twice returns the same
     line.
   - `next_line` returns `None` at the end of the source and does not raise.
5. An `## API` section listing the public names exported by the module, which are
   `LineSource` and `next_line`, `remaining`, `peek` as methods of `LineSource`.

## Constraints

- Every factual claim must be true of the code in this directory. Do not describe
  behaviour the code does not have.
- Do not invent parameters, return types, or exceptions.
- Use Markdown. Use fenced code blocks with a language tag for the example.
- The word `TODO` must not appear.
- Keep it under 60 lines.
