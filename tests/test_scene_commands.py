"""二维 Agent 命令协议与向量教学宏测试。"""

from __future__ import annotations

import unittest

from services.scene_commands import (
    CommandError,
    CommandPlan,
    SceneCommandService,
    RuleBasedAgentProvider,
)


class FakeHost:
    def __init__(self, fail: bool = False) -> None:
        self.operations: list[dict[str, object]] = []
        self.events: list[str] = []
        self.fail = fail

    def begin_scene_command_transaction(self) -> None:
        self.events.append("begin")

    def apply_scene_command(self, operation: dict[str, object]) -> None:
        self.operations.append(operation)
        if self.fail and len(self.operations) == 2:
            raise RuntimeError("forced failure")

    def commit_scene_command_transaction(self) -> None:
        self.events.append("commit")

    def rollback_scene_command_transaction(self) -> None:
        self.events.append("rollback")


class SceneCommandTests(unittest.TestCase):
    def test_rule_provider_generates_valid_vector_addition_plan(self) -> None:
        plan = RuleBasedAgentProvider().create_plan(
            "生成向量 a=(2,1) 和 b=(1,3)，显示平行四边形法和三角形法"
        )
        validation = SceneCommandService().preview(plan)

        self.assertTrue(validation.valid, validation.messages)
        sum_point = next(
            operation
            for operation in validation.expanded_operations
            if operation.get("op") == "point.upsert" and operation.get("alias") == "C"
        )
        self.assertEqual(sum_point["coordinates"], [3.0, 4.0])
        self.assertEqual(
            next(
                operation["text"]
                for operation in validation.expanded_operations
                if operation.get("op") == "annotation.upsert"
                and operation.get("alias") == "vector_addition_result"
            ),
            "a+b=(3, 4)",
        )

    def test_vector_macro_contains_dashed_parallelogram_and_triangle_rule(self) -> None:
        plan = CommandPlan(
            operations=(
                {
                    "op": "teach.vector_addition",
                    "a": [2, 1],
                    "b": [1, 3],
                    "show_parallelogram": True,
                    "show_triangle_rule": True,
                },
            )
        )
        operations = SceneCommandService().preview(plan).expanded_operations
        dashed = [operation for operation in operations if operation.get("style") == "dashed"]
        self.assertEqual({operation["alias"] for operation in dashed}, {"construction_a_to_c", "construction_b_to_c"})
        self.assertTrue(any(operation.get("alias") == "triangle_translated_b" for operation in operations))
        self.assertEqual(operations[-1], {"op": "view.fit", "padding": 1.15})

    def test_unknown_operation_is_rejected_before_execution(self) -> None:
        host = FakeHost()
        service = SceneCommandService(host)
        with self.assertRaises(CommandError):
            service.execute(CommandPlan(operations=({"op": "python.exec", "code": "1+1"},)))
        self.assertEqual(host.events, [])
        self.assertEqual(host.operations, [])

    def test_execution_is_atomic_and_rolls_back_on_host_failure(self) -> None:
        host = FakeHost(fail=True)
        service = SceneCommandService(host)
        plan = CommandPlan(
            operations=(
                {"op": "point.upsert", "alias": "O", "coordinates": [0, 0]},
                {"op": "point.upsert", "alias": "A", "coordinates": [2, 1]},
            )
        )

        with self.assertRaises(RuntimeError):
            service.execute(plan)
        self.assertEqual(host.events, ["begin", "rollback"])

    def test_curve_command_requires_safe_kind_and_expression(self) -> None:
        validation = SceneCommandService().preview(
            CommandPlan(
                operations=(
                    {"op": "curve.create", "alias": "f", "kind": "explicit", "expression": "y=sin(x)"},
                )
            )
        )
        self.assertTrue(validation.valid)
        invalid = SceneCommandService().preview(
            CommandPlan(
                operations=(
                    {"op": "curve.create", "alias": "f", "kind": "python", "expression": "__import__('os')"},
                )
            )
        )
        self.assertFalse(invalid.valid)

    def test_plan_parser_rejects_non_object_operations(self) -> None:
        with self.assertRaises(CommandError):
            CommandPlan.from_dict({"operations": ["scene.clear"]})


if __name__ == "__main__":
    unittest.main()
