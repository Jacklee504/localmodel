# Refactoring task

`severity.py` looks up severity weights from a module-level dictionary, but the same
weight table is also written out in `severity_label` as a chain of thresholds. Two places
to change means they drift apart.

## Requirements

1. Keep the public names `severity_for` and `severity_label`.
2. Keep the exact severity weights and the exact label boundaries
   (`high` at 0.7 and above, `medium` at 0.4 and above, otherwise `low`).
3. The label thresholds must be defined once, not duplicated as literals in two places.
4. `severity_label` must still return `"unknown"` for a change type that is not in the
   table.
5. Do not change behaviour for any input.
6. Add a short module-level comment explaining where the thresholds come from, so the
   next reader does not have to reverse-engineer them.
