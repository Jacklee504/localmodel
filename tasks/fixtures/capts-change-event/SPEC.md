# Change detection specification

Implement `changes.py`. It compares two versions of a pipeline definition and reports
what changed between them.

## Requirements

1. `detect_added(old_nodes, new_nodes) -> list[str]` returns the node names present in
   `new_nodes` but not in `old_nodes`, sorted.
2. `detect_removed(old_nodes, new_nodes) -> list[str]` returns the node names present in
   `old_nodes` but not in `new_nodes`, sorted.
3. `detect_renamed(old_nodes, new_nodes, hints) -> list[tuple[str, str]]` returns pairs of
   `(old_name, new_name)` for renames. A hint maps an old name to a new name. A rename is
   only reported when the old name is absent from `new_nodes`, the new name is absent from
   `old_nodes`, and the hint says so. The result is sorted by old name. A hint that
   conflicts with the node sets is ignored.
4. `detect_modified(old_nodes, new_nodes) -> list[str]` returns the names of nodes
   present in both sets whose definitions differ. A definition is a mapping of
   attributes. Two definitions are equal when they have the same keys and the same
   values. The result is sorted.
5. `detect_dependency_changes(old_dependencies, new_dependencies) -> list[tuple[str, str, str]]`
   returns `(node, dependency, kind)` triples where `kind` is either `"added"` or
   `"removed"`. A dependency is a node name. The result is sorted by node, then
   dependency, then kind.
6. `summarise(changes) -> dict[str, int]` returns a mapping of change kind to count,
   where the kinds are `added`, `removed`, `renamed`, `modified`, `dependency_added` and
   `dependency_removed`. Kinds with a count of zero are included.
7. `merge_changes(change_lists) -> list` concatenates lists of change tuples and returns
   them sorted, with duplicates removed.

## Constraints

- Use only the Python standard library.
- Do not modify any input.
- Node names are strings. A missing or empty node set is treated as an empty set.
