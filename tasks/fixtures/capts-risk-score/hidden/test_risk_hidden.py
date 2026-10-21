import unittest

from risk import CHANGE_SEVERITY, WEIGHTS, compute_risk_score, score_stages


class Change:
    def __init__(self, node_id, change_type):
        self.node_id = node_id
        self.change_type = change_type


class HiddenRiskTests(unittest.TestCase):
    def graph(self):
        dependencies = {
            "build": ["compile"],
            "test": ["build"],
            "deploy": ["build"],
            "compile": [],
        }
        pipelines = {"build": "main", "test": "main", "deploy": "main", "compile": "main"}
        return dependencies, pipelines

    def test_direct_dependency_scores_higher_than_indirect(self):
        dependencies, pipelines = self.graph()
        direct = compute_risk_score(
            (dependencies, pipelines), "build", "test", Change("build", "modified")
        )
        indirect = compute_risk_score(
            (dependencies, pipelines), "compile", "test", Change("compile", "modified")
        )
        self.assertGreater(direct.directness, indirect.directness)

    def test_more_dependents_scores_higher_fan_out(self):
        dependencies, pipelines = self.graph()
        many = compute_risk_score((dependencies, pipelines), "build", "build", Change("build", "modified"))
        few = compute_risk_score((dependencies, pipelines), "compile", "compile", Change("compile", "modified"))
        self.assertGreaterEqual(many.fan_out, few.fan_out)

    def test_cross_pipeline_is_detected(self):
        dependencies = {"a": [], "b": []}
        pipelines = {"a": "one", "b": "two"}
        score = compute_risk_score((dependencies, pipelines), "a", "b", Change("a", "modified"))
        self.assertGreater(score.cross_pipeline, 0.0)

    def test_same_pipeline_cross_pipeline_is_zero(self):
        dependencies, pipelines = self.graph()
        score = compute_risk_score((dependencies, pipelines), "build", "test", Change("build", "modified"))
        self.assertEqual(score.cross_pipeline, 0.0)

    def test_removed_change_scores_higher_than_added(self):
        dependencies, pipelines = self.graph()
        removed = compute_risk_score((dependencies, pipelines), "build", "test", Change("build", "removed"))
        added = compute_risk_score((dependencies, pipelines), "build", "test", Change("build", "dependency_added"))
        self.assertGreater(removed.change_severity, added.change_severity)

    def test_scores_are_deterministic(self):
        dependencies, pipelines = self.graph()
        first = compute_risk_score((dependencies, pipelines), "build", "test", Change("build", "modified"))
        second = compute_risk_score((dependencies, pipelines), "build", "test", Change("build", "modified"))
        self.assertEqual(first.overall, second.overall)
        self.assertEqual(first.level, second.level)

    def test_missing_affected_stage_raises_key_error(self):
        dependencies, pipelines = self.graph()
        with self.assertRaises(KeyError):
            compute_risk_score((dependencies, pipelines), "build", "absent", Change("build", "modified"))

    def test_scored_stage_carries_its_risk(self):
        dependencies, pipelines = self.graph()
        scored = score_stages((dependencies, pipelines), "build", Change("build", "modified"), ["test"])
        self.assertEqual(scored[0].risk.stage, "test")
        self.assertIsNone(scored[0].execution_result)

    def test_severity_table_has_the_six_named_changes(self):
        self.assertEqual(
            set(CHANGE_SEVERITY),
            {"removed", "renamed", "dependency_removed", "modified", "value_changed",
             "dependency_added"},
        )

    def test_weights_table_has_the_five_dimensions(self):
        self.assertEqual(
            set(WEIGHTS),
            {"critical_path", "fan_out", "directness", "change_severity", "cross_pipeline"},
        )
