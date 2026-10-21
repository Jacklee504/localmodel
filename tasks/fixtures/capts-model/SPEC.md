# Pipeline model specification

Implement `model.py`. It is the format-independent vocabulary of a pipeline analysis
tool: every other module refers to these types, so their names and shapes are fixed.

## Requirements

1. `NodeType` is a string enum with exactly the members `STAGE`, `VARIABLE`, `TEMPLATE`,
   `SCRIPT`. Their values are the lowercase member names.
2. `EdgeType` is a string enum with exactly the members `CONSUMES`, `INHERITS`,
   `DEPENDS_ON`, `EXECUTES`. Their values are the lowercase member names.
3. `ChangeType` is a string enum with exactly the members `ADDED`, `REMOVED`, `MODIFIED`,
   `RENAMED`. Their values are the lowercase member names.
4. `Verdict` is a string enum with exactly the members `PASS`, `FAIL`. Their values are
   the lowercase member names.
5. `NodeInfo` is a mutable dataclass with fields:
   - `id: str`
   - `node_type: NodeType`
   - `pipeline: str | None = None`
   - `metadata: dict[str, object]`, defaulting to an empty dict that is not shared between
     instances.
6. `EdgeInfo` is a mutable dataclass with fields `source: str`, `target: str`,
   `edge_type: EdgeType`.
7. `PipelineModel` is a mutable dataclass with fields `nodes: list[NodeInfo]`,
   `edges: list[EdgeInfo]`, and `triggers: dict[str, set[str]]`. Each list and dict must
   default to a fresh empty container, never a shared one.
8. `ChangeEvent` is a mutable dataclass with fields `node_id: str`,
   `change_type: ChangeType`, and `details: dict[str, object]` defaulting to an empty
   dict that is not shared between instances.
9. `ExecutionResult` is a frozen dataclass with fields `stage_id: str`, `exit_code: int`,
   `stdout: str = ""`, `stderr: str = ""`. It exposes a read-only property `passed`
   that is true exactly when `exit_code` is zero.
10. `FormatAdapter` is a runtime-checkable protocol. It declares:
    - `parse(path, *, pipeline_name=None) -> PipelineModel`
    - `detect_changes(old_pipeline, new_pipeline, *, pipeline_name="main",
      old_script_root=None, new_script_root=None) -> list[ChangeEvent]`
    - a static method `detect(directory) -> bool`
    - a static method `format_id() -> str`

## Constraints

- Use only the Python standard library.
- Do not add a dependency on `networkx` or any third-party package.
- Every public type must have a docstring.
- Keep the type annotations exactly as given above. Other modules import these names.
