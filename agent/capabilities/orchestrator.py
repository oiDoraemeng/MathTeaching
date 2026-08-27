"""Bounded, renderer-free orchestration of capability calls."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable

from agent.scene_snapshot import SceneSnapshot
from services.scene_commands import CommandPlan, SceneCommandService

from .contracts import (
    MAX_EXPANDED_PLAN_OPERATIONS,
    MAX_IDENTICAL_TOOL_CALLS,
    MAX_MUTATING_CALLS,
    MAX_RAW_PLAN_OPERATIONS,
    MAX_TOOL_CALLS,
    MAX_TOOL_RESULT_BYTES,
    CapabilityError,
    CapabilityResult,
    ToolCall,
)
from .registry import CapabilityRegistry, build_default_registry
from .scene_index import SceneIndex


@dataclass(frozen=True)
class CapabilityTurn:
    results: tuple[CapabilityResult, ...]
    index: SceneIndex
    plan: CommandPlan | None = None
    error: CapabilityResult | None = None


class CapabilityOrchestrator:
    """Stage successful capability fragments and compose one validated plan."""

    def __init__(self, registry: CapabilityRegistry | None = None, command_service: SceneCommandService | None = None) -> None:
        self.registry = registry or build_default_registry()
        self.command_service = command_service or SceneCommandService()

    def run_calls(self, calls: Iterable[ToolCall], snapshot: SceneSnapshot) -> CapabilityTurn:
        index = SceneIndex.from_snapshot(snapshot)
        results: list[CapabilityResult] = []
        operations: list[dict] = []
        raw_operation_count = 0
        target_scene: str | None = None
        seen: dict[str, int] = {}
        mutation_count = 0
        for call_number, call in enumerate(calls, start=1):
            if call_number > MAX_TOOL_CALLS:
                error = self._limit(call, "tool_call_limit", "单轮工具调用最多 8 次")
                return CapabilityTurn(tuple(results), index, error=error)
            canonical = self.registry.resolve_name(call.name) if self._known(call.name) else call.name
            key = ToolCall(call.call_id, canonical, call.arguments).normalized_key()
            seen[key] = seen.get(key, 0) + 1
            if seen[key] > MAX_IDENTICAL_TOOL_CALLS:
                error = self._limit(call, "tool_loop_detected", "检测到重复工具调用循环")
                return CapabilityTurn(tuple(results), index, error=error)
            spec = self.registry.get(canonical) if self._known(call.name) else None
            if spec is not None and spec.mutating:
                mutation_count += 1
                if mutation_count > MAX_MUTATING_CALLS:
                    error = self._limit(call, "mutation_limit", "单轮修改调用最多 4 次")
                    return CapabilityTurn(tuple(results), index, error=error)
            result = self.registry.dispatch(call, index)
            results.append(result)
            if len(json.dumps(result.to_dict(), ensure_ascii=False).encode("utf-8")) > MAX_TOOL_RESULT_BYTES:
                error = self._limit(call, "tool_result_limit", "工具结果超过 32 KiB 限制")
                return CapabilityTurn(tuple(results[:-1]), index, error=error)
            if result.status == "error":
                return CapabilityTurn(tuple(results), index, error=result)
            if result.plan is None:
                continue
            plan = CommandPlan.from_dict(result.plan)
            raw_operation_count += len(plan.operations)
            if raw_operation_count > MAX_RAW_PLAN_OPERATIONS:
                error = self._limit(call, "raw_plan_limit", "单轮原始计划操作最多 32 个")
                return CapabilityTurn(tuple(results), index, error=error)
            if target_scene is not None and plan.scene != target_scene:
                error = self._limit(call, "scene_conflict", "同一轮不能混合 2D 与 3D 目标场景")
                return CapabilityTurn(tuple(results), index, error=error)
            target_scene = plan.scene
            validation = self.command_service.preview(plan)
            if not validation.valid or len(validation.expanded_operations) + len(operations) > MAX_EXPANDED_PLAN_OPERATIONS:
                code = "expanded_plan_limit" if validation.valid else "invalid_command_plan"
                message = "展开后的计划操作最多 128 个" if validation.valid else "命令计划校验失败"
                error = self._limit(call, code, message)
                return CapabilityTurn(tuple(results), index, error=error)
            operations.extend(validation.expanded_operations)
            index.apply_operations(validation.expanded_operations)
        if target_scene is None:
            return CapabilityTurn(tuple(results), index)
        composed = CommandPlan(scene=target_scene, summary="；".join(CommandPlan.from_dict(item.plan).summary for item in results if item.plan), operations=tuple(operations))
        validation = self.command_service.preview(composed)
        if not validation.valid:
            return CapabilityTurn(tuple(results), index, error=self._limit(ToolCall("compose", "scene.edit", {}), "invalid_command_plan", "合成命令计划校验失败"))
        composed = CommandPlan(scene=target_scene, summary=composed.summary, operations=tuple(validation.expanded_operations))
        return CapabilityTurn(tuple(results), index, plan=composed)

    def _known(self, name: str) -> bool:
        try:
            self.registry.resolve_name(name)
        except ValueError:
            return False
        return True

    @staticmethod
    def _limit(call: ToolCall, code: str, message: str) -> CapabilityResult:
        return CapabilityResult.error(call.call_id, call.name, CapabilityError(code, message))
