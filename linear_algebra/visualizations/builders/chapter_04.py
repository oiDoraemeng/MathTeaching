"""Chapter 4 family-bound builders."""
from __future__ import annotations
from linear_algebra.visualizations.common import RenderContext
from services.scene_commands import CommandPlan

_IDS = ("space.closure", "subspace.classification", "subspace.intersection", "subspace.col-null", "span.dimension", "dependence.redundancy", "nullspace.test", "rank.collapse", "basis.span", "dimension.ladder", "coordinates.readout", "linear-map.definition", "linear-map.compare", "linear-map.matrix-columns", "kernel-image", "rank-nullity")

def _build(context: RenderContext) -> CommandPlan:
    topic = context.topic_id
    operation = {"op": "geometry.subspace_region", "alias": f"sem__{topic}", "basis": [[1.0, 0.0], [0.0, 1.0]], "bounds": list(context.bounds), "opacity": 0.2, "color": "#4c9f70"}
    if topic.endswith("coordinates.readout"):
        operation = {"op": "geometry.basis_grid", "alias": f"sem__{topic}", "basis_matrix": [[1.0, 0.0], [0.0, 1.0]], "standard_vector": [1.0, 2.0], "alternate_coordinates": [1.0, 2.0], "basis_alias": f"sem__{topic}__basis", "standard_alias": f"sem__{topic}__standard", "alternate_alias": f"sem__{topic}__alternate", "bounds": list(context.bounds)}
    return CommandPlan(scene="2d", operations=(operation, {"op": "view.fit", "padding": 1.15}), summary=f"Chapter 4 {topic}")

BUILDERS = {f"draw.ch04.{item}": _build for item in _IDS}
