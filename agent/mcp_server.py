"""本地 Math3D MCP 工具层。

这里实现的是进程内的 MCP 风格工具注册/调用协议，不开启网络端口，也不
接触 PyVista。工具先生成并校验 CommandPlan；只有显式传入 ``execute=True``
时才把计划交给 SceneCommandService。
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import sys
from typing import Any, Callable

from services.scene_commands import CommandPlan, SceneCommandService


@dataclass(frozen=True)
class MCPTool:
    name: str
    description: str
    handler: Callable[..., CommandPlan]


class Math3DMCPServer:
    name = "Math3D MCP"

    def __init__(self, command_service: SceneCommandService | None = None) -> None:
        self.command_service = command_service or SceneCommandService()
        self._tools: dict[str, MCPTool] = {
            "create_point": MCPTool("create_point", "创建二维或三维点", self.create_point),
            "create_vector": MCPTool("create_vector", "创建向量", self.create_vector),
            "create_curve": MCPTool("create_curve", "创建函数曲线", self.create_curve),
            "create_surface": MCPTool("create_surface", "创建曲面计划", self.create_surface),
            "add_annotation": MCPTool("add_annotation", "添加数学标注", self.add_annotation),
            "export_image": MCPTool("export_image", "导出当前场景图片", self.export_image),
            "calculate_intersection": MCPTool("calculate_intersection", "准备两个对象的交点计算", self.calculate_intersection),
        }

    @property
    def tools(self) -> tuple[MCPTool, ...]:
        return tuple(self._tools.values())

    def _validated_plan(self, plan: CommandPlan) -> CommandPlan:
        validation = self.command_service.preview(plan)
        if not validation.valid:
            raise ValueError("；".join(validation.messages))
        return plan

    def call_tool(self, name: str, *, execute: bool = False, **arguments: Any) -> CommandPlan:
        try:
            tool = self._tools[str(name)]
        except KeyError as error:
            raise ValueError(f"未知 MCP 工具: {name}") from error
        plan = tool.handler(**arguments)
        self._validated_plan(plan)
        if execute:
            if self.command_service.host is None:
                raise ValueError("MCP execute 需要绑定 SceneCommandService 宿主")
            self.command_service.execute(plan)
        return plan

    def handle_request(self, request: dict[str, Any] | str) -> dict[str, Any]:
        payload = json.loads(request) if isinstance(request, str) else dict(request)
        method = str(payload.get("method", ""))
        request_id = payload.get("id")
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": self.name, "version": "1.0"},
                    "capabilities": {"tools": {}},
                },
            }
        if method in {"tools/list", "list_tools"}:
            result = {"tools": [{"name": item.name, "description": item.description} for item in self.tools]}
            return {"jsonrpc": "2.0", "id": request_id, "result": result} if "jsonrpc" in payload else result
        if method in {"tools/call", "call_tool"}:
            params = dict(payload.get("params", {}))
            name = params.pop("name", "")
            plan = self.call_tool(name, **params)
            result = {"name": name, "content": [{"type": "text", "text": plan.to_json()}]}
            return {"jsonrpc": "2.0", "id": request_id, "result": result} if "jsonrpc" in payload else result
        raise ValueError(f"未知 MCP 方法: {method}")

    def serve_stdio(self, input_stream=None, output_stream=None) -> None:
        """提供可选的本地 stdin/stdout MCP 传输，不开启网络端口。"""
        source = input_stream or sys.stdin
        target = output_stream or sys.stdout
        for line in source:
            if not line.strip():
                continue
            try:
                response = self.handle_request(line)
            except Exception as error:
                response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32602, "message": str(error)}}
            target.write(json.dumps(response, ensure_ascii=False) + "\n")
            target.flush()

    def create_point(self, alias: str = "P", coordinates: list[float] | tuple[float, ...] = (0, 0), **kwargs: Any) -> CommandPlan:
        coordinates = list(coordinates)
        if len(coordinates) == 3:
            operation = {"op": "point3d.upsert", "alias": str(alias), "coordinates": coordinates, "name": kwargs.get("name", alias)}
            return self._validated_plan(CommandPlan(scene="3d", summary=f"创建三维点 {alias}", operations=(operation,)))
        operation = {"op": "point.upsert", "alias": str(alias), "coordinates": coordinates, "name": kwargs.get("name", alias)}
        return self._validated_plan(CommandPlan(summary=f"创建点 {alias}", operations=(operation,)))

    def create_vector(self, start: Any = "O", end: Any = "A", alias: str = "v", vector: Any = None, **kwargs: Any) -> CommandPlan:
        """创建已存在点之间的向量，或从坐标直接生成 O -> A。"""
        if vector is not None:
            if isinstance(vector, (list, tuple)) and len(vector) == 2 and not isinstance(start, (list, tuple)):
                start, end = [0, 0], list(vector)
            else:
                end = vector
        operations: list[dict[str, Any]] = []
        if isinstance(start, (list, tuple)) and isinstance(end, (list, tuple)):
            operations.extend(
                [
                    {"op": "point.upsert", "alias": "O", "coordinates": list(start), "name": "O"},
                    {"op": "point.upsert", "alias": "A", "coordinates": list(end), "name": "A"},
                ]
            )
            start, end = "O", "A"
        operations.append({"op": "linear.upsert", "alias": alias, "kind": "vector", "start": str(start), "end": str(end), "color": kwargs.get("color", "#2777b6")})
        return self._validated_plan(CommandPlan(summary=f"创建向量 {alias}", operations=tuple(operations)))

    def create_curve(self, expression: str, alias: str = "f", kind: str = "explicit", **kwargs: Any) -> CommandPlan:
        return self._validated_plan(CommandPlan(
            summary=f"创建曲线 {alias}",
            operations=({"op": "curve.create", "alias": alias, "kind": kind, "expression": expression},),
        ))

    def create_surface(self, expression: str, alias: str = "surface", kind: str = "explicit", **kwargs: Any) -> CommandPlan:
        return self._validated_plan(CommandPlan(
            scene="3d",
            summary=f"创建曲面 {alias}",
            operations=({"op": "surface.create", "alias": alias, "kind": kind, "expression": expression},),
        ))

    def add_annotation(self, text: str, position: list[float] | tuple[float, ...] = (0, 0), alias: str = "annotation", **kwargs: Any) -> CommandPlan:
        if len(position) != 2:
            raise ValueError("当前标注工具的位置必须是二维坐标")
        return self._validated_plan(CommandPlan(
            summary=f"添加标注 {alias}",
            operations=({"op": "annotation.upsert", "alias": alias, "text": text, "position": list(position), "latex": kwargs.get("latex"), "color": kwargs.get("color", "#263241")},),
        ))

    def export_image(self, filename: str) -> CommandPlan:
        return self._validated_plan(CommandPlan(summary="导出场景图片", operations=({"op": "scene.export_png", "filename": filename},)))

    def calculate_intersection(self, first: str, second: str, scene: str = "3d", **kwargs: Any) -> CommandPlan:
        return self._validated_plan(CommandPlan(scene=scene, summary="计算两个数学对象的交点", operations=({"op": "geometry.intersection", "first": first, "second": second},)))


MCPServer = Math3DMCPServer


if __name__ == "__main__":
    Math3DMCPServer().serve_stdio()
