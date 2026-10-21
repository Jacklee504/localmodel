import unittest
from dataclasses import FrozenInstanceError

from model import (
    ChangeEvent,
    ChangeType,
    EdgeInfo,
    EdgeType,
    ExecutionResult,
    FormatAdapter,
    NodeInfo,
    NodeType,
    PipelineModel,
    Verdict,
)


class HiddenModelTests(unittest.TestCase):
    def test_every_enum_has_exactly_the_specified_members(self):
        self.assertEqual(
            {member.name for member in NodeType},
            {"STAGE", "VARIABLE", "TEMPLATE", "SCRIPT"},
        )
        self.assertEqual(
            {member.name for member in EdgeType},
            {"CONSUMES", "INHERITS", "DEPENDS_ON", "EXECUTES"},
        )
        self.assertEqual(
            {member.name for member in ChangeType},
            {"ADDED", "REMOVED", "MODIFIED", "RENAMED"},
        )
        self.assertEqual({member.name for member in Verdict}, {"PASS", "FAIL"})

    def test_node_info_stores_its_fields(self):
        node = NodeInfo(id="n", node_type=NodeType.VARIABLE, pipeline="p", metadata={"k": 1})
        self.assertEqual(node.id, "n")
        self.assertEqual(node.node_type, NodeType.VARIABLE)
        self.assertEqual(node.pipeline, "p")
        self.assertEqual(node.metadata, {"k": 1})

    def test_edge_info_stores_its_fields(self):
        edge = EdgeInfo(source="a", target="b", edge_type=EdgeType.INHERITS)
        self.assertEqual((edge.source, edge.target, edge.edge_type), ("a", "b", EdgeType.INHERITS))

    def test_pipeline_model_accepts_populated_values(self):
        model = PipelineModel(
            nodes=[NodeInfo(id="n", node_type=NodeType.SCRIPT)],
            edges=[EdgeInfo(source="a", target="b", edge_type=EdgeType.EXECUTES)],
            triggers={"a": {"b"}},
        )
        self.assertEqual(len(model.nodes), 1)
        self.assertEqual(len(model.edges), 1)
        self.assertEqual(model.triggers, {"a": {"b"}})

    def test_change_event_stores_its_fields(self):
        event = ChangeEvent(node_id="n", change_type=ChangeType.RENAMED, details={"to": "m"})
        self.assertEqual(event.node_id, "n")
        self.assertEqual(event.change_type, ChangeType.RENAMED)
        self.assertEqual(event.details, {"to": "m"})

    def test_execution_result_keeps_streams(self):
        result = ExecutionResult(stage_id="s", exit_code=2, stdout="out", stderr="err")
        self.assertEqual(result.stdout, "out")
        self.assertEqual(result.stderr, "err")
        self.assertFalse(result.passed)

    def test_every_public_type_has_a_docstring(self):
        for name in (
            "NodeType", "EdgeType", "ChangeType", "Verdict", "NodeInfo", "EdgeInfo",
            "PipelineModel", "ChangeEvent", "ExecutionResult", "FormatAdapter",
        ):
            obj = globals()[name]
            self.assertTrue(obj.__doc__, f"{name} has no docstring")

    def test_format_adapter_declares_the_required_methods(self):
        for name in ("parse", "detect_changes", "detect", "format_id"):
            self.assertTrue(hasattr(FormatAdapter, name), f"FormatAdapter lacks {name}")

    def test_node_type_is_a_str_enum(self):
        self.assertTrue(issubclass(NodeType, str))
