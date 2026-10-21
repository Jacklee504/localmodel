# Docstring task

Add docstrings to every public function in `calculator.py`. Do not change the behaviour
of any function.

## Requirements

1. Every function in the module must have a docstring.
2. Each docstring must have a one-line summary that ends with a period.
3. Each docstring must document the parameters. Use the `param: type` style, one per
   line, under an `Args:` section.
4. Each docstring must document the return value under a `Returns:` section.
5. `divide` must document that it raises `ValueError` when the denominator is zero, in
   an `Raises:` section.
6. `mean` must document that it raises `ZeroDivisionError` when given an empty
   sequence, in a `Raises:` section. Do not change the exception type; the current
   behaviour is correct for this task.
7. `add` must not claim to raise anything, because it does not.
8. Do not change any function signature, body, or name.

## Return types to document

- `add` returns an `int` when both arguments are integers.
- `divide` returns a `float`.
- `mean` returns a `float`.

## Constraints

- Only the Python standard library may be used.
- The module must still import cleanly and the functions must still behave exactly as
  they did before.
