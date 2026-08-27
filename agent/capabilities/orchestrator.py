"""Bounded, renderer-free orchestration of sequential capability calls."""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass
class CapabilitySession:
    """One immutable-snapshot tool turn with a detached staged scene index."""

    registry: CapabilityRegistry
    command_service: SceneCommandService
    index: SceneIndex
    results: list[CapabilityResult] = field(default_factory=list)
    _operations: list[dict] = field(default_factory=list)
    _summaries: list[str] = field(default_factory=list)
    _target_scene: str | None = None
    _seen: dict[str, int] = field(default_factory=dict)
    _raw_operation_count: int = 0
    _mutation_count: int = 0
    _terminal_error: CapabilityResult | None = None

    @property
    def terminal_error(self) -> CapabilityResult | None:
        return self._terminal_error

    def dispatch(self, call: ToolCall) -> CapabilityResult:
        """Dispatch one call and stage only its preview-expanded operations."""
        if self._terminal_error is not None:
            return self._terminal_error
        if len(self.results) >= MAX_TOOL_CALLS:
            return self._terminate(call, "tool_call_limit", "单轮工具调用最多 8 次")
        try:
            canonical = self.registry.resolve_name(call.name)
            spec = self.registry.get(canonical)
        except ValueError:
            canonical = call.name
            spec = None
        key = ToolCall(call.call_id, canonical, call.arguments).normalized_key()
        self._seen[key] = self._seen.get(key, 0) + 1
        if self._seen[key] > MAX_IDENTICAL_TOOL_CALLS:
            return self._terminate(call, "tool_loop_detected", "检测到重复工具调用循环")
        if spec is not None and spec.mutating:
            self._mutation_count += 1
            if self._mutation_count > MAX_MUTATING_CALLS:
                return self._terminate(call, "mutation_limit", "单轮修改调用最多 4 次")
        result = self.registry.dispatch(call, self.index)
        if len(json.dumps(result.to_dict(), ensure_ascii=False).encode("utf-8")) > MAX_TOOL_RESULT_BYTES:
            return self._terminate(call, "tool_result_limit", "工具结果超过 32 KiB 限制")
        self.results.append(result)
        # Handler/schema errors are model-visible outcomes. They do not alter
        # staged state and allow a provider continuation to correct the call.
        if result.status == "error" or result.plan is None:
            return result
        plan = CommandPlan.from_dict(result.plan)
        self._raw_operation_count += len(plan.operations)
        if self._raw_operation_count > MAX_RAW_PLAN_OPERATIONS:
            return self._terminate(call, "raw_plan_limit", "单轮原始计划操作最多 32 个")
        if self._target_scene is not None and plan.scene != self._target_scene:
            return self._terminate(call, "scene_conflict", "同一轮不能混合 2D 与 3D 目标场景")
        self._target_scene = plan.scene
        validation = self.command_service.preview(plan)
        if not validation.valid:
            return self._terminate(call, "invalid_command_plan", "命令计划校验失败")
        if len(validation.expanded_operations) + len(self._operations) > MAX_EXPANDED_PLAN_OPERATIONS:
            return self._terminate(call, "expanded_plan_limit", "展开后的计划操作最多 128 个")
        self._operations.extend(validation.expanded_operations)
        self._summaries.append(plan.summary)
        self.index.apply_operations(validation.expanded_operations)
        return result

    def finish(self) -> CapabilityTurn:
        if self._terminal_error is not None:
            return CapabilityTurn(tuple(self.results), self.index, error=self._terminal_error)
        if self._target_scene is None:
            return CapabilityTurn(tuple(self.results), self.index)
        provisional = CommandPlan(scene=self._target_scene, summary="；".join(filter(None, self._summaries)), operations=tuple(self._operations))
        validation = self.command_service.preview(provisional)
        if not validation.valid:
            error = CapabilityResult.error("compose", "scene.edit", CapabilityError("invalid_command_plan", "合成命令计划校验失败"))
            return CapabilityTurn(tuple(self.results), self.index, error=error)
        return CapabilityTurn(
            tuple(self.results),
            self.index,
            plan=CommandPlan(scene=self._target_scene, summary=provisional.summary, operations=tuple(validation.expanded_operations)),
        )

    def _terminate(self, call: ToolCall, code: str, message: str) -> CapabilityResult:
        self._terminal_error = CapabilityResult.error(call.call_id, call.name, CapabilityError(code, message))
        return self._terminal_error


class CapabilityOrchestrator:
    """Create a staged session or process a fixed call sequence for tests."""

    def __init__(self, registry: CapabilityRegistry | None = None, command_service: SceneCommandService | None = None) -> None:
        self.registry = registry or build_default_registry()
        self.command_service = command_service or SceneCommandService()

    def start(self, snapshot: SceneSnapshot) -> CapabilitySession:
        return CapabilitySession(self.registry, self.command_service, SceneIndex.from_snapshot(snapshot))

    def run_calls(self, calls: Iterable[ToolCall], snapshot: SceneSnapshot) -> CapabilityTurn:
        session = self.start(snapshot)
        for call in calls:
            session.dispatch(call)
            if session.terminal_error is not None:
                break
        return session.finish()
