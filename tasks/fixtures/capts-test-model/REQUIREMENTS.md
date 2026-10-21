# Test writing task

Write unit tests for `ledger.py` in `tests/test_ledger.py`.

## Requirements

1. Use `unittest`, not `pytest`.
2. Cover every public function in `ledger.py`: `normalise_entry`, `total_amount`, and
   `group_by_kind`.
3. For `normalise_entry`:
   - a string amount is converted to an `int`;
   - a missing amount defaults to `0`;
   - a mixed-case kind is lowercased;
   - a missing kind becomes the empty string;
   - a missing `ref` becomes `None`;
   - a `ref` that is present is preserved unchanged.
4. For `total_amount`:
   - the amounts of several entries are summed;
   - an empty list totals `0`;
   - a string amount is still counted as a number.
5. For `group_by_kind`:
   - entries are counted per kind;
   - kinds differing only in case are counted together;
   - an empty list gives an empty mapping.
6. Do not change `ledger.py`.
7. The test file must import from `ledger`, so that it can be run from this directory
   with `python3 -m unittest discover -s tests -v`.
