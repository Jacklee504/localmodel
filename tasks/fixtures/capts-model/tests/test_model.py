import unittest
from dataclasses import FrozenInstanceError

from model import (
    ChangeEvent,
    ChangeType,
    EdgeInfo,
    EdgeType,
    ExecutionResult,
    NodeInfo,
    NodeType,
    PipelineModel,
    Verdict,
)


class ModelTests(unittest.TestCase):
    def test_enum_members_and_values(self):
        self.assertEqual([m.value for m in NodeType], ["stage", "variable", "template", "script"])
        self.assertEqual(
            [m.value for m in EdgeType], ["consumes", "inherits", "depends_on", "executes"]
        )
        self.assertEqual([m.value for m in ChangeType], ["added", "removed", "modified", "renamed"])
        self.assertEqual([m.value for m in Verdict], ["pass", "fail"])

    def test_enums_are_strings(self):
        self.assertEqual(NodeType.STAGE, "stage")
        self.assertIsInstance(NodeType.STAGE, str)

    def test_node_info_defaults(self):
        node = NodeInfo(id="build", node_type=NodeType.STAGE)
        self.assertIsNone(node.pipeline)
        self.assertEqual(node.metadata, {})

    def test_metadata_is_not_shared(self):
        first = NodeInfo(id="a", node_type=NodeType.STAGE)
        second = NodeInfo(id="b", node_type=NodeType.STAGE)
        first.metadata["x"] = 1
        self.assertEqual(second.metadata, {})

    def test_pipeline_model_defaults_are_not_shared(self):
        first = PipelineModel()
        second = PipelineModel()
        first.nodes.append(NodeInfo(id="a", node_type=NodeType.STAGE))
        first.edges.append(EdgeInfo(source="a", target="b", edge_type=EdgeType.CONSUMES))
        first.triggers["a"] = {"b"}
        self.assertEqual(second.nodes, [])
        self.assertEqual(second.edges, [])
        self.assertEqual(second.triggers, {})

    def test_change_event_details_not_shared(self):
        first = ChangeEvent(node_id="a", change_type=ChangeType.ADDED)
        second = ChangeEvent(node_id="b", change_type=ChangeType.ADDED)
        first.details["note"] = "x"
        self.assertEqual(second.details, {})

    def test_execution_result_passed_property(self):
        self.assertTrue(ExecutionResult(stage_id="s", exit_code=0).passed)
        self.assertFalse(ExecutionResult(stage_id="s", exit_code=1).passed)
        self.assertEqual(ExecutionResult(stage_id="s", exit_code=0).stdout, "")

    def test_execution_result_is_frozen(self):
        result = ExecutionResult(stage_id="s", exit_code=0)
        with self.assertRaises(FrozenInstanceError):
            result.exit_code = 1

    def test_format_adapter_protocol_is_runtime_checkable(self):
        from typing import runtime_checkable

        from model import FormatAdapter

        class Adapter:
            def parse(self, path, *, pipeline_name=None):
                return PipelineModel()

            def detect_changes(self, old_pipeline, new_pipeline, *, pipeline_name="main",
                              old_script_root=None, new_script_root=None):
                return []

            @staticmethod
            def detect(directory):
                return True

            @staticmethod
            def format_id():
                return "demo"

        self.assertTrue(isinstance(Adapter(), FormatAdapter))
        self.assertFalse(isinstance(object(), FormatAdapter))
