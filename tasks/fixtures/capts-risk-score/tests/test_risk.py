import unittest

from risk import (
    CHANGE_SEVERITY,
    WEIGHTS,
    RiskScore,
    ScoredStage,
    compute_risk_score,
    score_stages,
)


class Change:
    def __init__(self, node_id, change_type):
        self.node_id = node_id
        self.change_type = change_type


class RiskTests(unittest.TestCase):
    def graph(self):
        dependencies = {
            "build": ["compile"],
            "test": ["build"],
            "deploy": ["build"],
            "compile": [],
        }
        pipelines = {"build": "main", "test": "main", "deploy": "main", "compile": "main"}
        return dependencies, pipelines

    def test_severity_and_weight_tables(self):
        self.assertEqual(CHANGE_SEVERITY["removed"], 1.0)
        self.assertEqual(CHANGE_SEVERITY["renamed"], 0.9)
        self.assertEqual(CHANGE_SEVERITY["dependency_removed"], 0.8)
        self.assertEqual(CHANGE_SEVERITY["modified"], 0.7)
        self.assertEqual(CHANGE_SEVERITY["value_changed"], 0.5)
        self.assertEqual(CHANGE_SEVERITY["dependency_added"], 0.2)
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0)

    def test_score_shape(self):
        dependencies, pipelines = self.graph()
        score = compute_risk_score((dependencies, pipelines), "compile", "test", Change("compile", "modified"))
        self.assertIsInstance(score, RiskScore)
        self.assertEqual(score.stage, "test")
        for value in (
            score.overall, score.critical_path, score.fan_out,
            score.directness, score.change_severity, score.cross_pipeline,
        ):
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_overall_is_weighted_sum(self):
        dependencies, pipelines = self.graph()
        score = compute_risk_score((dependencies, pipelines), "compile", "test", Change("compile", "modified"))
        expected = (
            score.critical_path * WEIGHTS["critical_path"]
            + score.fan_out * WEIGHTS["fan_out"]
            + score.directness * WEIGHTS["directness"]
            + score.change_severity * WEIGHTS["change_severity"]
            + score.cross_pipeline * WEIGHTS["cross_pipeline"]
        )
        self.assertAlmostEqual(score.overall, round(expected, 4), places=4)

    def test_level_thresholds(self):
        dependencies, pipelines = self.graph()
        score = compute_risk_score((dependencies, pipelines), "compile", "test", Change("compile", "removed"))
        if score.overall >= 0.75:
            self.assertEqual(score.level, "high")
        elif score.overall >= 0.40:
            self.assertEqual(score.level, "medium")
        else:
            self.assertEqual(score.level, "low")

    def test_unknown_change_type_has_zero_severity(self):
        dependencies, pipelines = self.graph()
        score = compute_risk_score((dependencies, pipelines), "compile", "test", Change("compile", "invented"))
        self.assertEqual(score.change_severity, 0.0)

    def test_missing_node_raises_key_error(self):
        dependencies, pipelines = self.graph()
        with self.assertRaises(KeyError):
            compute_risk_score((dependencies, pipelines), "absent", "test", Change("absent", "modified"))

    def test_score_stages_preserves_order(self):
        dependencies, pipelines = self.graph()
        scored = score_stages((dependencies, pipelines), "compile", Change("compile", "modified"), ["deploy", "test"])
        self.assertEqual([item.stage_id for item in scored], ["deploy", "test"])
        self.assertIsInstance(scored[0], ScoredStage)
        self.assertIsNone(scored[0].execution_result)

    def test_inputs_are_not_modified(self):
        dependencies, pipelines = self.graph()
        before = {key: list(value) for key, value in dependencies.items()}
        compute_risk_score((dependencies, pipelines), "compile", "test", Change("compile", "modified"))
        self.assertEqual(dependencies, before)
