# Deterministic risk scoring specification

Implement `risk.py`. It scores how risky it is that one pipeline stage is affected by a
change. Scoring must be deterministic: the same inputs always give the same numbers.

## The model

A pipeline is a directed graph. An edge runs from a dependent node to the node it
depends on. A change to one node therefore affects everything that transitively depends
on it.

## Requirements

1. `CHANGE_SEVERITY` maps a change name to a severity weight:
   `removed` 1.0, `renamed` 0.9, `dependency_removed` 0.8, `modified` 0.7,
   `value_changed` 0.5, `dependency_added` 0.2.
2. `WEIGHTS` maps a risk dimension to its contribution:
   `critical_path` 0.30, `fan_out` 0.20, `directness` 0.20, `change_severity` 0.20,
   `cross_pipeline` 0.10. The weights sum to 1.0.
3. `RiskScore` is a frozen dataclass with fields `stage: str`, `overall: float`,
   `critical_path: float`, `fan_out: float`, `directness: float`,
   `change_severity: float`, `cross_pipeline: float`, `level: str`.
4. `ScoredStage` is a frozen dataclass with fields `stage_id: str`, `risk: RiskScore`,
   and `execution_result: ExecutionResult | None = None`.
5. `compute_risk_score(graph, changed_node, affected_stage, change) -> RiskScore`
   calculates and returns the score. `change` carries a `change_type` name and a
   `node_id`.
6. The five dimension scores are each in the range 0.0 to 1.0.
7. `overall` is the weighted sum of the five dimensions using `WEIGHTS`. It is rounded
   to four decimal places.
8. `level` is derived from `overall`:
   - `overall >= 0.75` gives `high`
   - `overall >= 0.40` gives `medium`
   - otherwise `low`
9. The dimensions are:
   - `critical_path`: how close the affected stage is to the end of the longest path it
     participates in. A stage that many other stages depend on scores higher.
   - `fan_out`: how many stages depend directly on the affected stage. More dependents
     means a higher score.
   - `directness`: how directly the changed node affects the affected stage. A stage that
     depends directly on the changed node scores higher than one that depends on it
     through a long chain.
   - `change_severity`: the `CHANGE_SEVERITY` weight of the change type.
   - `cross_pipeline`: whether the change crosses a pipeline boundary, that is, the
     changed node and the affected stage belong to different pipelines.
10. `score_stages(graph, changed_node, change, stages) -> list[ScoredStage]` scores each
    stage in `stages`, in the order given.
11. If the change type is not in `CHANGE_SEVERITY`, treat its severity as 0.0.
12. If the changed node is not in the graph, or the affected stage is not in the graph,
    raise `KeyError` naming the missing node.

## Constraints

- Use only the Python standard library. A graph is passed in as a mapping of node name
  to a sequence of node names it depends on, and a mapping of node name to its pipeline
  name.
- Keep every dimension in the range 0.0 to 1.0.
- Do not modify the inputs.
