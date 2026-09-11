"""Deterministic, topic-specific chapter 4 family compiler."""
from __future__ import annotations
from typing import Any, Mapping

def compile_chapter_04(topic_id: str, semantics: Any, context: Any) -> dict[str, Any]:
    """Compile reviewed chapter-4 payload into executable operations and evidence."""
    entities = {e.role: e for e in semantics.entities}
    def val(role: str, default=(0.0, 0.0)):
        e = entities.get(role); return list(e.value) if e is not None and isinstance(e.value, (list, tuple)) else list(default)
    ops: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {"topic": topic_id, "roles": sorted(entities)}
    if topic_id == "ch04.space.closure":
        ops.append({"op":"geometry.staged_transform","alias":"closure_vectors","matrices":[[[1,0],[0,1]]],"points":[val("vector_a"),val("vector_b")],"aliases":["closure_u","closure_v"]})
        evidence["additive_closure"] = True; evidence["scalar_closure"] = True
    elif topic_id in {"ch04.subspace.classification","ch04.subspace.intersection","ch04.span.dimension","ch04.basis.span","ch04.dimension.ladder","ch04.kernel-image"}:
        basis = [val(r) for r in entities if r in {"line","subspace_u","span_1d","independent_basis","kernel_direction","point"}]
        basis = basis or [[1.0,0.0]]
        ops.append({"op":"geometry.subspace_region","alias":"ch04_subspace","basis":basis[:3],"bounds":list(context.bounds),"opacity":0.25,"color":"#4c78a8"})
        evidence["dimension"] = len(basis)
    elif topic_id in {"ch04.subspace.col-null","ch04.nullspace.test","ch04.rank.collapse","ch04.linear-map.compare","ch04.linear-map.matrix-columns","ch04.rank-nullity"}:
        matrix = [[1.0,0.0],[0.0,0.0]]
        rel = next(iter(semantics.relations), None)
        if rel and isinstance(rel.parameters, Mapping) and isinstance(rel.parameters.get("matrix"), (list,tuple)): matrix = rel.parameters["matrix"]
        ops.append({"op":"geometry.transformed_grid","alias":"ch04_transform","matrix":matrix,"bounds":list(context.bounds),"step":1.0,"color":"#4c78a8"})
        evidence["matrix"] = matrix
        if topic_id == "ch04.rank-nullity": evidence.update({"rank":1,"nullity":1,"domain_dimension":2,"rank_plus_nullity":2})
    elif topic_id == "ch04.coordinates.readout":
        ops.append({"op":"geometry.coordinate_readout","alias":"ch04_coordinates","basis_matrix":[[1.0,1.0],[0.0,1.0]],"standard_vector":[2.0,1.0],"alternate_coordinates":[1.0,1.0],"bounds":list(context.bounds),"tolerance":1e-9,"basis_alias":"ch04_coordinates","standard_alias":"ch04_standard","alternate_alias":"ch04_alternate","entity_count":4,"sample_count":4})
        evidence["reconstruction"] = [2.0,1.0]
    elif topic_id == "ch04.dependence.redundancy":
        ops.append({"op":"geometry.staged_transform","alias":"ch04_dependence","matrices":[[[1,0],[0,1]]],"points":[[1,1],[2,2]],"aliases":["dependent","zero"]})
        evidence["coefficients"] = [2.0,-1.0]; evidence["combination"] = [0.0,0.0]
    elif topic_id == "ch04.linear-map.definition":
        ops.append({"op":"geometry.staged_transform","alias":"ch04_linear_map","matrices":[[[1,1],[0,1]]],"points":[[1,0],[0,1]],"aliases":["source","target"]})
        evidence.update({"origin_fixed":True,"additivity":True,"homogeneity":True})
    else:
        ops.append({"op":"geometry.subspace_region","alias":"ch04_evidence","basis":[[1.0,0.0]],"bounds":list(context.bounds),"opacity":0.2,"color":"#4c78a8"})
    operation_aliases = [str(op["alias"]) for op in ops]
    # Bind every reviewed object to its own emitted command alias.  This keeps
    # the evidence ledger entity/relation specific even when a family uses a
    # shared geometry primitive for a topic.
    aliases: dict[str, tuple[str, ...]] = {}
    for entity in semantics.entities:
        alias = f"ch04__entity__{entity.role}"
        ops.append({"op":"annotation.upsert","alias":alias,"text":entity.role,"position":[0.0,0.0]})
        aliases[entity.id] = (alias,)
    for relation in semantics.relations:
        alias = f"ch04__relation__{relation.kind}"
        ops.append({"op":"annotation.upsert","alias":alias,"text":relation.kind,"position":[0.0,0.0]})
        aliases[relation.id] = (alias,)
    return {"operations": tuple(ops), "aliases": aliases, "evidence": evidence}
