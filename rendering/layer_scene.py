"""Incremental actor management for independently editable surface layers."""

from __future__ import annotations

from itertools import combinations

import pyvista as pv

from geometry.cas_surface import ExpressionError, build_surface_mesh, parse_surface_expression
from geometry.intersection import intersect_surface_meshes
from models.surface_layer import PlotDomain, SurfaceLayer
from rendering.materials import MATERIAL_PRESETS, material_preset


class LayerRenderError(RuntimeError):
    """Raised when a layer has no usable surface mesh in the current domain."""


class LayerSceneController:
    """Own surface and intersection actors while leaving axes and lights untouched."""

    def __init__(
        self,
        plotter: pv.Plotter,
        domain: PlotDomain | None = None,
        *,
        ambient: float = 0.2,
        material_name: str = "光泽塑料",
    ) -> None:
        self.plotter = plotter
        self.domain = domain or PlotDomain()
        self.ambient = max(0.0, min(1.0, float(ambient)))
        self.material_name = material_name if material_name in MATERIAL_PRESETS else "光泽塑料"
        self.layers: dict[str, SurfaceLayer] = {}
        self.meshes: dict[str, pv.PolyData] = {}
        self.auto_intersections = True
        self.intersections_visible = True
        self.manual_intersection_pairs: set[tuple[str, str]] = set()

    def add_layer(self, layer: SurfaceLayer) -> None:
        if layer.id in self.layers:
            raise KeyError(f"图层 {layer.id} 已存在。")
        mesh = self._mesh_for(layer)
        self.layers[layer.id] = layer
        self.meshes[layer.id] = mesh
        self._replace_surface_actor(layer, mesh)
        self._refresh_intersections()

    def update_layer(self, layer: SurfaceLayer) -> None:
        if layer.id not in self.layers:
            raise KeyError(f"未知图层: {layer.id}")
        mesh = self._mesh_for(layer)
        self._remove_intersections_for(layer.id)
        self.layers[layer.id] = layer
        self.meshes[layer.id] = mesh
        self._replace_surface_actor(layer, mesh)
        self._refresh_intersections()

    def remove_layer(self, layer_id: str) -> None:
        if layer_id not in self.layers:
            return
        self.plotter.remove_actor(self.surface_actor_name(layer_id), render=False)
        self._remove_intersections_for(layer_id)
        self.layers.pop(layer_id, None)
        self.meshes.pop(layer_id, None)
        self.manual_intersection_pairs = {pair for pair in self.manual_intersection_pairs if layer_id not in pair}

    def set_visible(self, layer_id: str, visible: bool) -> None:
        layer = self._layer(layer_id)
        layer.visible = visible
        self._actor(self.surface_actor_name(layer_id)).visibility = visible
        self._refresh_intersection_visibility()

    def set_intersections_visible(self, layer_id: str, visible: bool) -> None:
        self._layer(layer_id).intersections_visible = visible
        self._refresh_intersection_visibility()

    def set_intersection_color(self, layer_id: str, color: str, revision: int | None = None) -> None:
        """Update all related actors; the newest function-level choice wins."""
        layer = self._layer(layer_id)
        layer.intersection_color = color
        layer.intersection_color_revision = (
            int(revision)
            if revision is not None
            else layer.intersection_color_revision + 1
        )
        for pair in self._existing_intersection_pairs():
            if layer_id in pair:
                self.plotter.remove_actor(self.intersection_actor_name(*pair), render=False)
        self._refresh_intersections()

    def set_color(self, layer_id: str, color: str) -> None:
        layer = self._layer(layer_id)
        layer.color = color
        self._replace_surface_actor(layer, self.meshes[layer_id])

    def set_opacity(self, layer_id: str, opacity: float) -> None:
        layer = self._layer(layer_id)
        layer.opacity = max(0.05, min(1.0, float(opacity)))
        self._replace_surface_actor(layer, self.meshes[layer_id])

    def set_ambient(self, ambient: float) -> None:
        self.ambient = max(0.0, min(1.0, float(ambient)))
        for layer_id in self.layers:
            actor = self._actor(self.surface_actor_name(layer_id))
            prop = getattr(actor, "prop", None)
            if prop is not None:
                prop.ambient = self.ambient

    def set_material(self, material_name: str) -> None:
        self.material_name = material_name if material_name in MATERIAL_PRESETS else "光泽塑料"
        for layer_id, layer in self.layers.items():
            self._replace_surface_actor(layer, self.meshes[layer_id])

    def set_global_intersections_visible(self, visible: bool) -> None:
        self.intersections_visible = visible
        self._refresh_intersection_visibility()

    def set_auto_intersections(self, enabled: bool) -> None:
        self.auto_intersections = enabled
        self._refresh_intersections()

    def set_manual_intersection_pair(self, first_id: str, second_id: str, enabled: bool) -> None:
        pair = self._pair(first_id, second_id)
        if first_id not in self.layers or second_id not in self.layers:
            raise KeyError("所选交线对中的两个图层都必须存在。")
        if enabled:
            self.manual_intersection_pairs.add(pair)
        else:
            self.manual_intersection_pairs.discard(pair)
        self._refresh_intersections()

    def set_domain(self, domain: PlotDomain) -> None:
        previous_domain = self.domain
        self.domain = domain
        try:
            rebuilt = {
                layer_id: self._mesh_for(layer)
                for layer_id, layer in self.layers.items()
            }
        except Exception:
            self.domain = previous_domain
            raise
        for pair in self._existing_intersection_pairs():
            self.plotter.remove_actor(self.intersection_actor_name(*pair), render=False)
        self.domain = domain
        self.meshes = rebuilt
        for layer_id, layer in self.layers.items():
            self._replace_surface_actor(layer, self.meshes[layer_id])
        self._refresh_intersections()

    @staticmethod
    def surface_actor_name(layer_id: str) -> str:
        return f"layer:{layer_id}:surface"

    @staticmethod
    def intersection_actor_name(first_id: str, second_id: str) -> str:
        first_id, second_id = sorted((first_id, second_id))
        return f"intersection:{first_id}:{second_id}"

    def _mesh_for(self, layer: SurfaceLayer) -> pv.PolyData:
        try:
            expression = parse_surface_expression(layer.expression, layer.kind)
            mesh = build_surface_mesh(expression, layer.parameters, self.domain.scaled(layer.range_scale))
        except ExpressionError:
            raise
        except Exception as error:
            raise LayerRenderError(f"无法创建曲面“{layer.name}”。") from error
        if mesh.n_points == 0 or mesh.n_cells == 0:
            raise LayerRenderError(f"曲面“{layer.name}”未与当前绘图范围相交。")
        return mesh

    def _replace_surface_actor(self, layer: SurfaceLayer, mesh: pv.PolyData) -> None:
        self.plotter.remove_actor(self.surface_actor_name(layer.id), render=False)
        actor = self.plotter.add_mesh(
            mesh,
            name=self.surface_actor_name(layer.id),
            color=layer.color,
            opacity=layer.opacity,
            ambient=self.ambient,
            **self._surface_material(),
        )
        actor.visibility = layer.visible

    def _surface_material(self) -> dict:
        preset = material_preset(self.material_name)
        return {
            "smooth_shading": bool(preset["smooth_shading"]),
            "diffuse": float(preset["diffuse"]),
            "specular": float(preset["specular"]),
            "specular_power": float(preset["specular_power"]),
        }

    def _refresh_intersections(self) -> None:
        wanted_pairs = self._wanted_intersection_pairs()
        existing_pairs = self._existing_intersection_pairs()
        for pair in existing_pairs - wanted_pairs:
            self.plotter.remove_actor(self.intersection_actor_name(*pair), render=False)
        for pair in wanted_pairs:
            name = self.intersection_actor_name(*pair)
            if name in self._actors():
                continue
            curve = intersect_surface_meshes(self.meshes[pair[0]], self.meshes[pair[1]])
            if curve.n_points == 0 or curve.n_cells == 0:
                continue
            actor = self.plotter.add_mesh(
                curve,
                name=name,
                color=self._intersection_color(pair),
                line_width=1.5,
                render_lines_as_tubes=False,
            )
            actor.visibility = self._intersection_is_visible(pair)
        self._refresh_intersection_visibility()

    def _wanted_intersection_pairs(self) -> set[tuple[str, str]]:
        visible_ids = [layer.id for layer in self.layers.values() if layer.visible]
        if self.auto_intersections:
            return {self._pair(first_id, second_id) for first_id, second_id in combinations(visible_ids, 2)}
        return {
            pair
            for pair in self.manual_intersection_pairs
            if self.layers[pair[0]].visible and self.layers[pair[1]].visible
        }

    def _existing_intersection_pairs(self) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for name in self._actors():
            if not name.startswith("intersection:"):
                continue
            _, first_id, second_id = name.split(":", 2)
            pairs.add((first_id, second_id))
        return pairs

    def _remove_intersections_for(self, layer_id: str) -> None:
        for pair in self._existing_intersection_pairs():
            if layer_id in pair:
                self.plotter.remove_actor(self.intersection_actor_name(*pair), render=False)

    def _refresh_intersection_visibility(self) -> None:
        for pair in self._existing_intersection_pairs():
            self._actor(self.intersection_actor_name(*pair)).visibility = self._intersection_is_visible(pair)

    def _intersection_is_visible(self, pair: tuple[str, str]) -> bool:
        first, second = (self.layers[layer_id] for layer_id in pair)
        return self.intersections_visible and first.visible and second.visible and first.intersections_visible and second.intersections_visible

    def _intersection_color(self, pair: tuple[str, str]) -> str:
        first, second = (self.layers[layer_id] for layer_id in pair)
        latest = max(
            (first, second),
            key=lambda layer: (layer.intersection_color_revision, layer.id),
        )
        return latest.intersection_color

    def _actors(self) -> dict:
        renderer = getattr(self.plotter, "renderer", None)
        if renderer is not None:
            return renderer.actors
        return self.plotter.actors

    def _actor(self, name: str):
        try:
            return self._actors()[name]
        except KeyError as error:
            raise KeyError(f"缺少绘制对象: {name}") from error

    def _layer(self, layer_id: str) -> SurfaceLayer:
        try:
            return self.layers[layer_id]
        except KeyError as error:
            raise KeyError(f"未知图层: {layer_id}") from error

    @staticmethod
    def _pair(first_id: str, second_id: str) -> tuple[str, str]:
        if first_id == second_id:
            raise ValueError("An intersection pair must contain two distinct layers.")
        return tuple(sorted((first_id, second_id)))
