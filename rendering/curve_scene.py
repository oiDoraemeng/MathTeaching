"""Incremental actor management for editable two-dimensional curve layers."""

from __future__ import annotations

import pyvista as pv

from geometry.cas_curve import CurveExpressionError, build_curve_mesh, parse_curve_expression
from models.curve_layer import CurveLayer, Plot2DDomain


class CurveRenderError(RuntimeError):
    """Raised when a curve has no usable geometry in the current domain."""


class CurveSceneController:
    """Own curve actors while leaving the Cartesian grid untouched."""

    def __init__(self, plotter: pv.Plotter, domain: Plot2DDomain | None = None) -> None:
        self.plotter = plotter
        self.domain = domain or Plot2DDomain()
        self.layers: dict[str, CurveLayer] = {}
        self.meshes: dict[str, pv.PolyData] = {}

    @staticmethod
    def actor_name(layer_id: str) -> str:
        return f"curve:{layer_id}"

    def add_layer(self, layer: CurveLayer) -> None:
        if layer.id in self.layers:
            raise KeyError(f"图层 {layer.id} 已存在。")
        mesh = self._mesh_for(layer)
        self.layers[layer.id] = layer
        self.meshes[layer.id] = mesh
        self._replace_actor(layer, mesh)

    def update_layer(self, layer: CurveLayer) -> None:
        if layer.id not in self.layers:
            raise KeyError(f"未知曲线图层: {layer.id}")
        mesh = self._mesh_for(layer)
        self.layers[layer.id] = layer
        self.meshes[layer.id] = mesh
        self._replace_actor(layer, mesh)

    def remove_layer(self, layer_id: str) -> None:
        self.plotter.remove_actor(self.actor_name(layer_id), render=False)
        self.layers.pop(layer_id, None)
        self.meshes.pop(layer_id, None)

    def set_visible(self, layer_id: str, visible: bool) -> None:
        layer = self._layer(layer_id)
        layer.visible = visible
        try:
            self._actor(layer_id).visibility = visible
        except KeyError:
            # Curves outside the current viewport have no actor until they re-enter it.
            pass

    def set_color(self, layer_id: str, color: str) -> None:
        layer = self._layer(layer_id)
        layer.color = color
        self._replace_actor_if_present(layer)

    def set_line_width(self, layer_id: str, line_width: float) -> None:
        layer = self._layer(layer_id)
        layer.line_width = max(1.0, min(8.0, float(line_width)))
        self._replace_actor_if_present(layer)

    def set_domain(self, domain: Plot2DDomain) -> None:
        """Resample every curve for a new visible viewport without losing layers."""
        previous_domain = self.domain
        self.domain = domain
        rebuilt: dict[str, pv.PolyData] = {}
        try:
            for layer_id, layer in self.layers.items():
                try:
                    rebuilt[layer_id] = self._mesh_for(layer)
                except CurveRenderError:
                    # A layer can simply be outside the current viewport; keep its data model.
                    rebuilt[layer_id] = pv.PolyData()
        except Exception:
            self.domain = previous_domain
            raise
        self.meshes = rebuilt
        for layer_id, layer in self.layers.items():
            mesh = self.meshes[layer_id]
            if mesh.n_points == 0 or mesh.n_cells == 0:
                self.plotter.remove_actor(self.actor_name(layer_id), render=False)
                continue
            self._replace_actor(layer, mesh)

    def _mesh_for(self, layer: CurveLayer) -> pv.PolyData:
        try:
            expression = parse_curve_expression(layer.expression, layer.kind)
            mesh = build_curve_mesh(expression, layer.parameters, self.domain.scaled(layer.range_scale))
        except CurveExpressionError:
            raise
        except Exception as error:
            raise CurveRenderError(f"无法创建函数“{layer.name}”。") from error
        if mesh.n_points == 0 or mesh.n_cells == 0:
            raise CurveRenderError(f"函数“{layer.name}”未与当前绘图范围相交。")
        return mesh

    def _replace_actor(self, layer: CurveLayer, mesh: pv.PolyData) -> None:
        self.plotter.remove_actor(self.actor_name(layer.id), render=False)
        actor = self.plotter.add_mesh(
            mesh,
            name=self.actor_name(layer.id),
            color=layer.color,
            line_width=layer.line_width,
            render_lines_as_tubes=False,
            lighting=False,
        )
        actor.visibility = layer.visible

    def _replace_actor_if_present(self, layer: CurveLayer) -> None:
        mesh = self.meshes[layer.id]
        if mesh.n_points == 0 or mesh.n_cells == 0:
            self.plotter.remove_actor(self.actor_name(layer.id), render=False)
            return
        self._replace_actor(layer, mesh)

    def _actor(self, layer_id: str):
        try:
            return self.plotter.renderer.actors[self.actor_name(layer_id)]
        except (AttributeError, KeyError):
            return self.plotter.actors[self.actor_name(layer_id)]

    def _layer(self, layer_id: str) -> CurveLayer:
        try:
            return self.layers[layer_id]
        except KeyError as error:
            raise KeyError(f"未知曲线图层: {layer_id}") from error
