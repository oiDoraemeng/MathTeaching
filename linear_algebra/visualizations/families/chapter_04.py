"""Strict, computed Chapter 4 semantic family compiler."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping
from types import MappingProxyType

from linear_algebra.chapter_04_semantics import Chapter4Semantic, semantic_for
from linear_algebra.teaching.model import VisualEntity, VisualRelation, VisualSemantics
from ..compiler import CompileIssue, VisualCompileError

TOL = 1e-9


@dataclass(frozen=True)
class Chapter4CompileResult:
    operations: tuple[dict[str, Any], ...]
    aliases: Mapping[str, tuple[str, ...]]
    evidence: Mapping[str, object]


def _fail(code: str, path: str, message: str) -> CompileIssue:
    return CompileIssue(code, path, message)


def _close(left: object, right: object) -> bool:
    if isinstance(left, Mapping) or isinstance(right, Mapping):
        return isinstance(left, Mapping) and isinstance(right, Mapping) and set(left) == set(right) and all(_close(left[k], right[k]) for k in left)
    if isinstance(left, (tuple, list)) or isinstance(right, (tuple, list)):
        return isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)) and len(left) == len(right) and all(_close(a, b) for a, b in zip(left, right))
    if isinstance(left, (int, float)) and not isinstance(left, bool) and isinstance(right, (int, float)) and not isinstance(right, bool):
        return math.isclose(float(left), float(right), rel_tol=TOL, abs_tol=TOL)
    return left == right


def _vector(value: object, dimension: int | None = None) -> list[float]:
    if not isinstance(value, (tuple, list)) or not value or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value):
        raise ValueError("expected numeric vector")
    result = [float(v) for v in value]
    if dimension is not None and len(result) != dimension:
        raise ValueError("vector dimension mismatch")
    if not all(math.isfinite(v) for v in result):
        raise ValueError("non-finite vector")
    return result


def _matrix(value: object) -> list[list[float]]:
    if not isinstance(value, (tuple, list)) or not value:
        raise ValueError("expected matrix")
    rows = [_vector(row) for row in value]
    if not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("ragged matrix")
    return rows


def _rank(value: object) -> int:
    rows = _matrix(value)
    work = [row[:] for row in rows]
    rank = 0
    for column in range(len(work[0])):
        pivot = next((index for index in range(rank, len(work)) if abs(work[index][column]) > TOL), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        scale = work[rank][column]
        work[rank] = [v / scale for v in work[rank]]
        for index in range(len(work)):
            if index != rank:
                factor = work[index][column]
                work[index] = [a - factor * b for a, b in zip(work[index], work[rank])]
        rank += 1
    return rank


def _matvec(matrix: object, vector: object) -> list[float]:
    rows = _matrix(matrix)
    x = _vector(vector, len(rows[0]))
    return [sum(a * b for a, b in zip(row, x)) for row in rows]


def _add(a: object, b: object) -> list[float]:
    left = _vector(a); right = _vector(b, len(left))
    return [x + y for x, y in zip(left, right)]


def _scale(value: object, scalar: float) -> list[float]:
    return [scalar * x for x in _vector(value)]


def _combination(basis: object, coefficients: object) -> list[float]:
    vectors = _matrix(basis); coeffs = _vector(coefficients, len(vectors))
    return [sum(coeffs[i] * vectors[i][j] for i in range(len(vectors))) for j in range(len(vectors[0]))]


def _in_span(basis: object, vector: object) -> bool:
    rows = _matrix(basis); return _rank(rows) == _rank([*rows, _vector(vector, len(rows[0]))])


def _same_span(first: object, second: object) -> bool:
    return _rank(first)==_rank(second) and all(_in_span(first,v) for v in _matrix(second))


def _cross(a: object, b: object) -> list[float]:
    x = _vector(a, 3); y = _vector(b, 3)
    return [x[1]*y[2]-x[2]*y[1], x[2]*y[0]-x[0]*y[2], x[0]*y[1]-x[1]*y[0]]


def _entity_alias(role: str) -> str: return f"ch04__entity__{role}"
def _relation_alias(name: str) -> str: return f"ch04__relation__{name}"


def _primary_entity_alias(role: str, entity: VisualEntity) -> str:
    alias = _entity_alias(role)
    if entity.dimension == 3 and entity.kind in {"matrix", "basis", "subspace"} and _rank(entity.value) == 3:
        return f"{alias}__axis_1"
    return alias


def _bounds(context: Any, dimension: int) -> list[float]:
    values = list(context.bounds)
    return values if dimension == 2 else (values if len(values) == 6 else [values[0], values[1], values[2], values[3], -3.0, 3.0])


def _layout_operations(topic: str, role: str, operations: list[dict[str,Any]]) -> list[dict[str,Any]]:
    """Translate each complete witness into its comparison/domain lane."""
    if topic=="ch04.linear-map.compare":
        lanes={"rotation":(-8,4),"stretch":(0,4),"projection":(8,4),"translation":(-8,-4),"square_map":(0,-4),"constant_shift":(8,-4)}
        offset=lanes.get(role,(0,0))
    elif topic=="ch04.subspace.col-null":
        offset=(4,0) if role in {"codomain","column_space","image_vector","zero"} else (-4,0)
    else:
        return operations
    for operation in operations:
        if operation["op"]=="point.upsert":
            operation["coordinates"]=_add(operation["coordinates"],offset)
        elif operation["op"] in {"geometry.subspace_region","geometry.transformed_grid"}:
            operation["origin"]=_add(operation.get("origin",[0,0]),offset)
            operation["bounds"]=[-1.25,1.25,-1.25,1.25]
        elif operation["op"]=="geometry.polygon":
            operation["vertices"]=[_add(v,offset) for v in operation["vertices"]]
        elif operation["op"]=="curve.create":
            operation["expression"]=f"y=(x-({offset[0]}))^2+({offset[1]})"
    return operations


def _normal(basis: list[list[float]]) -> list[float]:
    result = _cross(basis[0], basis[1])
    if math.sqrt(sum(v*v for v in result)) <= TOL:
        raise ValueError("plane basis is dependent")
    return result


def _entity_operations(entity: VisualEntity, alias: str, scene: str, context: Any) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    ops: list[dict[str, Any]] = []
    if scene == "2d":
        if entity.kind == "point":
            ops.append({"op":"point.upsert","alias":alias,"coordinates":_vector(entity.value,2),"name":entity.label})
        elif entity.kind == "vector":
            origin=f"{alias}__origin"; end=f"{alias}__end"
            ops.extend(({"op":"point.upsert","alias":origin,"coordinates":[0.0,0.0],"name":"O"}, {"op":"point.upsert","alias":end,"coordinates":_vector(entity.value,2),"name":entity.label}, {"op":"linear.upsert","alias":alias,"start":origin,"end":end,"kind":"vector","role":"primary"}))
        elif entity.kind == "matrix":
            ops.append({"op":"geometry.transformed_grid","alias":alias,"matrix":_matrix(entity.value),"bounds":_bounds(context,2),"step":1.0})
        elif entity.kind in {"basis","subspace","region"}:
            basis=_matrix(entity.value)
            if entity.role in {"standard_basis", "oblique_basis"}:
                basis=[list(column) for column in zip(*basis)]
            ops.append({"op":"geometry.subspace_region","alias":alias,"basis":basis[:2],"bounds":_bounds(context,2),"opacity":0.2})
            # The region protocol accepts two directions; render every member
            # separately so a redundant third generator is never discarded.
            if entity.kind == "basis":
                for index, vector in enumerate(basis, 1):
                    ops.extend(_vector_relation(f"{alias}__generator_{index}",vector))
        elif entity.kind == "affine_set":
            ops.append({"op":"geometry.subspace_region","alias":alias,"basis":[[1.0,0.0],[0.0,1.0]],"origin":_vector(entity.value,2),"bounds":_bounds(context,2),"opacity":0.16})
        elif entity.kind == "constraint":
            ops.append({"op":"curve.create","alias":alias,"kind":"explicit","expression":"y=x^2"})
        else:
            raise ValueError(f"unsupported 2d entity kind {entity.kind}")
        return ops, (alias,)

    if entity.kind == "point":
        ops.append({"op":"point3d.upsert","alias":alias,"coordinates":_vector(entity.value,3),"name":entity.label})
        return ops, (alias,)
    if entity.kind == "vector":
        vector=_vector(entity.value,3)
        if any(abs(v)>TOL for v in vector):
            ops.append({"op":"linear3d.upsert","alias":alias,"start":[0.0,0.0,0.0],"end":vector,"kind":"vector","role":"primary"})
        else:
            ops.append({"op":"point3d.upsert","alias":alias,"coordinates":vector,"name":entity.label})
        return ops, (alias,)
    if entity.kind == "affine_set":
        basis=_matrix(entity.value)
        ops.append({"op":"plane3d.upsert","alias":alias,"origin":basis[-1],"normal":_normal(basis[:2]),"size":2.5,"opacity":0.2})
        return ops, (alias,)
    if entity.kind in {"matrix","basis","subspace","region"}:
        vectors=_matrix(entity.value)
        if entity.kind == "matrix":
            vectors=[list(column) for column in zip(*vectors)]
        rank=_rank(vectors)
        if entity.kind == "basis" and entity.role == "independent_set" and rank == 3:
            ops.append({"op":"geometry.parallelepiped","alias":alias,"origin":[0.0,0.0,0.0],"vectors":vectors[:3],"opacity":0.16})
            return ops, (alias,)
        if rank == 2:
            ops.append({"op":"plane3d.upsert","alias":alias,"origin":[0.0,0.0,0.0],"normal":_normal(vectors),"size":2.5,"opacity":0.2})
            return ops, (alias,)
        if rank == 1:
            vector=next(v for v in vectors if any(abs(x)>TOL for x in v))
            ops.append({"op":"linear3d.upsert","alias":alias,"start":_scale(vector,-2.0),"end":_scale(vector,2.0),"kind":"segment","role":"primary"})
            return ops, (alias,)
        aliases=[]
        for index, vector in enumerate(vectors[:3], 1):
            axis=f"{alias}__axis_{index}"; aliases.append(axis)
            if any(abs(x)>TOL for x in vector):
                ops.append({"op":"linear3d.upsert","alias":axis,"start":[0.0,0.0,0.0],"end":vector,"kind":"vector","role":"primary"})
            else:
                ops.append({"op":"point3d.upsert","alias":axis,"coordinates":[0.0,0.0,0.0],"name":"0"})
        return ops, tuple(aliases)
    raise ValueError(f"unsupported 3d entity kind {entity.kind}")


def _parameters(relation: VisualRelation) -> Mapping[str, object]:
    return relation.parameters


def _vector_relation(alias: str, endpoint: object) -> list[dict[str, Any]]:
    origin=f"{alias}__origin"; end=f"{alias}__end"
    return [{"op":"point.upsert","alias":origin,"coordinates":[0.0,0.0],"name":"O"},
            {"op":"point.upsert","alias":end,"coordinates":_vector(endpoint,2),"name":"result"},
            {"op":"linear.upsert","alias":alias,"start":origin,"end":end,"kind":"vector","role":"result"}]


def _coordinate_operation(alias: str, basis: object, coordinates: object, vector: object, context: Any) -> dict[str, Any]:
    return {"op":"geometry.coordinate_readout","alias":alias,"basis_matrix":_matrix(basis),
            "standard_vector":_vector(vector,2),"alternate_coordinates":_vector(coordinates,2),
            "bounds":_bounds(context,2),"tolerance":TOL,"basis_alias":f"{alias}__basis",
            "standard_alias":f"{alias}__standard","alternate_alias":f"{alias}__alternate",
            "entity_count":4,"sample_count":4}


def _coordinate_operations(alias: str, basis: object, coordinates: object, vector: object, context: Any) -> list[dict[str, Any]]:
    readout=_coordinate_operation(alias,basis,coordinates,vector,context)
    grid={**readout,"op":"geometry.basis_grid","alias":f"{alias}__grid"}
    operations=[grid,readout]
    endpoint=[0.0,0.0]
    for index,(column,coefficient) in enumerate(zip(zip(*_matrix(basis)),_vector(coordinates)),1):
        next_endpoint=_add(endpoint,_scale(column,coefficient))
        term=f"{alias}__component_{index}"
        operations.extend([
            {"op":"point.upsert","alias":f"{term}__start","coordinates":endpoint},
            {"op":"point.upsert","alias":f"{term}__end","coordinates":next_endpoint},
            {"op":"linear.upsert","alias":term,"start":f"{term}__start","end":f"{term}__end","kind":"vector","role":"result"},
        ])
        endpoint=next_endpoint
    return operations


def _relation_operations(topic_id: str, relation: VisualRelation, entities: Mapping[str, VisualEntity], context: Any) -> list[dict[str, Any]]:
    alias=_relation_alias(relation.id.rsplit(".",1)[-1]); p=_parameters(relation)
    source=entities[relation.source_ref]; target=entities[relation.target_ref]
    if source.dimension == 2:
        if relation.kind == "coordinate_equivalence":
            return _coordinate_operations(alias,p["basis_matrix"],p["coordinates"],p["expected_vector"],context)
        if relation.kind == "same_measure":
            spec=semantic_for(topic_id); by_role={e.role:e for e in entities.values()}
            basis=by_role["oblique_basis"].value; coords=by_role["oblique_coordinates"].value; vector=by_role["same_vector"].value
            return _coordinate_operations(alias,basis,coords,vector,context)
        if topic_id == "ch04.linear-map.matrix-columns" and relation.kind == "image_of":
            by_role={e.role:e for e in entities.values()}; a=_vector(by_role["column_1"].value,2); b=_vector(by_role["column_2"].value,2)
            return [{"op":"geometry.polygon","alias":alias,"vertices":[[0.0,0.0],a,_add(a,b),b],"opacity":0.14,"outline":True}]
        if relation.kind in {"maps_to","column_image","rank_of","image_of","kernel_of","classification"}:
            matrix=p.get("matrix")
            if matrix is None and source.kind == "matrix": matrix=source.value
            if matrix is None and target.kind == "matrix": matrix=target.value
            if matrix is not None and len(_matrix(matrix)) == 2:
                return [{"op":"geometry.transformed_grid","alias":alias,"matrix":_matrix(matrix),"bounds":_bounds(context,2),"step":1.0}]
        if relation.kind in {"sum","additivity"}:
            if relation.kind == "sum":
                a=_vector(source.value,2); b=_vector(p.get("other_vector"),2)
            else:
                by_role={e.role:e for e in entities.values()}; a=_vector(by_role["T_u"].value,2); b=_vector(by_role["T_v"].value,2)
            result=_add(a,b)
            return [{"op":"geometry.polygon","alias":alias,"vertices":[[0.0,0.0],a,result,b],"opacity":0.16,"outline":True}]
        if relation.kind in {"scalar_multiple","homogeneity"}:
            return _vector_relation(alias,target.value)
        if relation.kind == "not_linear":
            if source.kind == "constraint": return [{"op":"curve.create","alias":alias,"kind":"explicit","expression":"y=x^2"}]
            return _vector_relation(alias,p["origin_image"])
        if relation.kind == "basis_of" or (relation.kind in {"dimension_of","linear_dependence","contains"} and source.kind in {"basis","subspace"}):
            return _entity_operations(source,alias,"2d",context)[0]
        # A target redrawn with a relation-specific alias is a geometric
        # witness of the typed relation, never a text-only bookkeeping edge.
        return _entity_operations(target,alias,"2d",context)[0]

    if relation.kind == "intersects_in":
        return [{"op":"geometry.intersection","alias":alias,"first":_primary_entity_alias(source.role,source),"second":_primary_entity_alias(target.role,target)}]
    if relation.kind == "linear_combination":
        vectors=[_scale(vector,coefficient) for vector,coefficient in zip(_matrix(source.value),_vector(p["coefficients"]))]
        operations=[]; endpoint=[0.0,0.0,0.0]
        for index,vector in enumerate(vectors,1):
            end=_add(endpoint,vector)
            operations.append({"op":"linear3d.upsert","alias":f"{alias}__term_{index}","start":endpoint,"end":end,"kind":"vector","role":"result"})
            endpoint=end
        operations.append({"op":"point3d.upsert","alias":alias,"coordinates":endpoint,"name":"zero combination"})
        return operations
    if relation.kind in {"union_counterexample","linear_combination","sum"}:
        if relation.kind == "union_counterexample":
            by_role={e.role:e for e in entities.values()}; vectors=[_vector(by_role["union_u"].value,3),_vector(by_role["union_v"].value,3)]
        else:
            vectors=_matrix(source.value)[:2] if source.kind in {"basis","matrix"} else [_vector(source.value,3),_vector(p.get("other_vector"),3)]
        return [{"op":"geometry.parallelogram3d","alias":alias,"origin":[0.0,0.0,0.0],"vectors":vectors,"opacity":0.16}]
    if relation.kind == "null_solution" and relation.id.endswith("nontrivial_solution"):
        columns=[list(column) for column in zip(*_matrix(source.value))]
        coefficients=_vector(target.value,len(columns))
        vectors=[_scale(column,coefficient) for column,coefficient in zip(columns,coefficients)]
        operations=[{"op":"geometry.parallelogram3d","alias":alias,"origin":[0.0,0.0,0.0],"vectors":vectors[:2],"opacity":0.16}]
        endpoint=[0.0,0.0,0.0]
        for index,vector in enumerate(vectors,1):
            next_endpoint=_add(endpoint,vector)
            operations.append({"op":"linear3d.upsert","alias":f"{alias}__term_{index}","start":endpoint,"end":next_endpoint,"kind":"vector","role":"result"})
            endpoint=next_endpoint
        operations.append({"op":"point3d.upsert","alias":f"{alias}__residual","coordinates":endpoint,"name":"Ax"})
        return operations
    if relation.kind == "affine_translation":
        basis=_matrix(source.value)
        return [{"op":"plane3d.upsert","alias":alias,"origin":_vector(p["offset"],3),"normal":_normal(basis),"size":2.5,"opacity":0.16}]
    return _entity_operations(target,alias,"3d",context)[0]


def _mathematical_evidence(topic_id: str, by_role: Mapping[str, VisualEntity], relations: tuple[VisualRelation, ...] = ()) -> dict[str, object]:
    """Recompute the advertised theorem from entity values, not labels."""
    value=lambda role: by_role[role].value
    checks: dict[str,bool] = {}
    numbers: dict[str,object] = {}
    parameters={relation.id.rsplit(".",1)[-1]:relation.parameters for relation in relations}
    if topic_id == "ch04.space.closure":
        checks["additive_closure"]=_close(_add(value("vector_a"),value("vector_b")),value("sum")) and _in_span(value("space"),value("sum"))
        checks["scalar_closure"]=_close(_scale(value("vector_a"),2),value("scaled")) and _in_span(value("space"),value("scaled"))
    elif topic_id == "ch04.subspace.classification":
        dimensions=[0,_rank(value("line")),_rank(value("plane")),_rank(value("whole_space"))]
        offset=_matrix(value("affine_counterexample"))[-1]
        origin=_vector(value("origin"),3)
        checks.update(classification_dimensions=dimensions==[0,1,2,3],origin_contains=_close(origin,[0,0,0]) and all(_in_span(value(role),origin) for role in ("line","plane","whole_space")),affine_not_subspace=not _in_span(_matrix(value("affine_counterexample"))[:2],_scale(offset,-1))); numbers.update(dimensions=dimensions,affine_offset=offset)
    elif topic_id == "ch04.subspace.intersection":
        u=value("subspace_u"); v=value("subspace_v"); inter=value("intersection"); total=value("union_sum")
        checks["intersection_closed"]=_rank(inter)==1 and all(_in_span(u,x) and _in_span(v,x) for x in _matrix(inter))
        checks["union_not_closed"]=_close(_add(value("union_u"),value("union_v")),total) and not _in_span(u,total) and not _in_span(v,total)
    elif topic_id == "ch04.subspace.col-null":
        matrix=value("map_A"); checks["diag_1_0"]=_close(matrix,[[1,0],[0,0]])
        checks["kernel_to_zero"]=_close(_matvec(matrix,value("kernel_vector")),[0,0]) and _in_span(value("kernel"),value("kernel_vector"))
        columns=[list(column) for column in zip(*_matrix(matrix))]
        image_basis=_matrix(value("column_space"))
        image_parameters=parameters["domain_image"]
        sample=image_parameters["input_vector"]
        image=_matvec(matrix,sample)
        checks["image_x_axis"]=_rank(image_basis)==_rank(columns)==1 and all(_in_span(image_basis,column) for column in columns) and all(_in_span(columns,v) for v in image_basis) and _close(image,value("image_vector")) and _in_span(image_basis,image)
        numbers.update(columns=columns,image=image,image_rank=_rank(columns))
    elif topic_id == "ch04.span.dimension":
        ranks=[_rank(value(f"span_{i}d")) for i in (1,2,3)]; numbers["ranks"]=ranks
        checks.update(span_rank_1=ranks[0]==1,span_rank_2=ranks[1]==2,span_rank_3=ranks[2]==3,rank_equals_dimension=ranks==[1,2,3])
    elif topic_id == "ch04.dependence.redundancy":
        combination=_combination(value("dependent_set"),value("coefficients")); numbers["combination"]=combination
        checks["nonzero_coefficients_sum_zero"]=_close(combination,[0,0,0]) and any(abs(x)>TOL for x in _vector(value("coefficients")))
        checks["independent_full_rank"]=_rank(value("independent_set"))==3
    elif topic_id == "ch04.nullspace.test":
        result=_matvec(value("columns"),value("null_vector")); numbers["Ax"]=result
        columns=[list(column) for column in zip(*_matrix(value("columns")))]
        terms=[_scale(column,coefficient) for column,coefficient in zip(columns,_vector(value("null_vector")))]
        numbers.update(columns=columns,combination_terms=terms,combination_residual=_combination(columns,value("null_vector")))
        checks["Ax_zero"]=_close(result,[0,0,0]); checks["nonzero_null_solution"]=any(abs(x)>TOL for x in _vector(value("null_vector"))) and checks["Ax_zero"]
        checks["trivial_nullspace_only"]=_rank(value("independent_columns"))==3
    elif topic_id == "ch04.rank.collapse":
        ranks=[_rank(value(role)) for role in ("rank_two","rank_one","rank_zero")]; numbers["ranks"]=ranks
        columns=lambda role: [list(c) for c in zip(*_matrix(value(role)))]
        checks.update(rank_two_plane=ranks[0]==2 and _same_span(columns("rank_two"),value("plane_image")),rank_one_line=ranks[1]==1 and _same_span(columns("rank_one"),value("line_image")),rank_zero_point=ranks[2]==0 and _close(value("point_image"),_matvec(value("rank_zero"),[1,1])),rank_collapse_sequence=ranks==[2,1,0])
    elif topic_id == "ch04.basis.span":
        complete=_rank(value("independent_basis")); few=_rank(value("too_few")); many=_rank(value("too_many")); numbers.update(complete_rank=complete,too_few_rank=few,too_many_rank=many)
        checks.update(independent_and_spanning=complete==2,too_few_not_spanning=few==1,too_many_redundant=many==2 and len(_matrix(value("too_many")))==3)
    elif topic_id == "ch04.dimension.ladder":
        dims=[0,_rank(value("line")),_rank(value("plane")),_rank(value("volume"))]; numbers["dimensions"]=dims
        lower=_in_span(value("line"),value("point")) and all(_in_span(value("plane"),v) for v in _matrix(value("line")))
        upper=all(_in_span(value("volume"),v) for v in _matrix(value("plane")))
        checks.update(nested_0_1_2=dims[:3]==[0,1,2] and lower,nested_dimensions=dims==[0,1,2,3] and lower and upper)
    elif topic_id == "ch04.coordinates.readout":
        standard=_matvec(value("standard_basis"),value("standard_coordinates")); alternate=_matvec(value("oblique_basis"),value("oblique_coordinates")); numbers.update(standard=standard,alternate=alternate)
        checks["standard_reconstruction"]=_close(standard,value("same_vector")); checks["coordinate_reconstruction"]=_close(alternate,value("same_vector"))
    elif topic_id == "ch04.linear-map.definition":
        matrix=value("map_T"); Tu=_matvec(matrix,value("u")); Tv=_matvec(matrix,value("v")); Tsum=_matvec(matrix,value("sum_test")); Tscaled=_matvec(matrix,value("homogeneity_test"))
        scalar=float(parameters["input_scaling"]["scalar"])
        checks["origin_fixed"]=_close(value("origin"),[0,0]) and _close(_matvec(matrix,value("origin")),value("origin"))
        checks["additivity"]=_close(value("sum_test"),_add(value("u"),value("v"))) and _close(Tu,value("T_u")) and _close(Tv,value("T_v")) and _close(Tsum,_add(Tu,Tv)) and _close(Tsum,value("T_sum"))
        checks["homogeneity"]=_close(value("homogeneity_test"),_scale(value("u"),scalar)) and _close(Tu,value("T_u")) and _close(Tscaled,_scale(Tu,scalar)) and _close(Tscaled,value("T_scaled"))
    elif topic_id == "ch04.linear-map.compare":
        diagnostics={}
        for role in ("rotation","stretch","projection"):
            matrix=value(role); p=parameters[f"{role}_linear"]
            origin=_matvec(matrix,value("origin"))
            Tu=_matvec(matrix,p["u"]); Tv=_matvec(matrix,p["v"])
            sum_image=_matvec(matrix,_add(p["u"],p["v"]))
            scaled_image=_matvec(matrix,_scale(p["u"],float(p["scalar"])))
            diagnostics[role]={"origin":origin,"image_u":Tu,"image_v":Tv,"sum_image":sum_image,"sum_of_images":_add(Tu,Tv),"scaled_image":scaled_image,"scaled_output":_scale(Tu,float(p["scalar"]))}
            diagnostics[role]["passes"]=(
                _close(origin,[0,0]) and _close(origin,p["origin_image"])
                and _close(Tu,p["image_u"]) and _close(Tv,p["image_v"])
                and _close(sum_image,_add(Tu,Tv)) and _close(sum_image,p["sum_image"])
                and _close(scaled_image,_scale(Tu,float(p["scalar"]))) and _close(scaled_image,p["scaled_image"])
            )
        numbers["linear_diagnostics"]=diagnostics
        checks["linear_examples_pass_axioms"]=all(item["passes"] for item in diagnostics.values())
        translation=_vector(value("translation")); shift=_vector(value("constant_shift")); samples=_matrix(value("square_map"))
        square_parameters=parameters["square_failure"]
        inputs=_vector(square_parameters["inputs"],2)
        sum_image=sum(inputs)**2; separate_sum=sum(x*x for x in inputs)
        square_failure=all(math.isclose(y,x*x,rel_tol=TOL,abs_tol=TOL) for x,y in samples) and not math.isclose(sum_image,separate_sum,rel_tol=TOL,abs_tol=TOL) and _close(sum_image,square_parameters.get("sum_image")) and _close(separate_sum,square_parameters.get("separate_sum"))
        numbers.update(square_inputs=inputs,square_sum_image=sum_image,square_separate_sum=separate_sum)
        checks["nonlinear_diagnostics"]=any(abs(x)>TOL for x in translation) and any(abs(x)>TOL for x in shift) and square_failure
    elif topic_id == "ch04.linear-map.matrix-columns":
        matrix=value("map_T"); c1=_matvec(matrix,value("standard_e1")); c2=_matvec(matrix,value("standard_e2")); numbers.update(column_1=c1,column_2=c2)
        checks["Tej_equals_column_j"]=_close(c1,value("column_1")) and _close(c2,value("column_2")); checks["columns_determine_grid"]=_rank([c1,c2])==2
    elif topic_id == "ch04.kernel-image":
        matrix=value("map_T"); checks["kernel_maps_zero"]=_close(_matvec(matrix,value("kernel_direction")),[0,0]); checks["image_reachable"]=_close(_matvec(matrix,value("sample_input")),value("sample_output")) and _in_span(value("image"),value("sample_output"))
    elif topic_id == "ch04.rank-nullity":
        matrix=_matrix(value("map_T")); dimension=len(matrix[0]); rank=_rank(matrix); nullity=dimension-rank; numbers.update(rank=rank,nullity=nullity,domain_dimension=dimension)
        kernel_valid=_rank(value("nullity"))==nullity and all(_close(_matvec(matrix,v),[0]*len(matrix)) for v in _matrix(value("nullity")))
        collapsed_valid=_in_span(value("nullity"),value("collapsed")) and _close(_matvec(matrix,value("collapsed")),value("zero")) and _close(value("zero"),[0]*len(matrix))
        image_valid=_same_span([list(c) for c in zip(*matrix)],value("rank"))
        direct_sum=_rank([*_matrix(value("preserved")),_vector(value("collapsed"))])==dimension and all(_in_span(value("domain"),v) for v in [*_matrix(value("preserved")),_vector(value("collapsed"))])
        preserved_images=[_matvec(matrix,v) for v in _matrix(value("preserved"))]
        checks["preserved_plus_collapsed"]=collapsed_valid and direct_sum and _same_span(preserved_images,value("rank"))
        checks["rank_plus_nullity_equals_domain"]=kernel_valid and image_valid and rank+nullity==_rank(value("domain"))==dimension
    failed=[name for name,valid in checks.items() if not valid]
    if failed:
        raise VisualCompileError(tuple(_fail("mathematical_invariant",f"$.visual_semantics.invariants.{name}","recomputed invariant is false") for name in failed))
    return {"topic":topic_id,"invariants":checks,**numbers}


class Chapter4FamilyCompiler:
    """Validate one exact topic graph and emit its real geometric witnesses."""

    @classmethod
    def validate(cls, topic_id: str, semantics: VisualSemantics) -> tuple[CompileIssue, ...]:
        try:
            spec=semantic_for(topic_id)
        except KeyError:
            return (_fail("unsupported_topic","$.topic_id",topic_id),)
        issues: list[CompileIssue]=[]
        if semantics.scene_kind != spec.scene_kind:
            issues.append(_fail("scene_kind_mismatch","$.visual_semantics.scene_kind",spec.scene_kind))
        if semantics.scene_family != spec.family:
            issues.append(_fail("scene_family_mismatch","$.visual_semantics.scene_family",spec.family))

        expected_roles={item.role:item for item in spec.entities}
        actual_roles={item.role:item for item in semantics.entities}
        for role in sorted(set(expected_roles)-set(actual_roles)):
            issues.append(_fail("missing_entity_role","$.visual_semantics.entities",role))
        for role in sorted(set(actual_roles)-set(expected_roles)):
            issues.append(_fail("unexpected_entity_role","$.visual_semantics.entities",role))
        if len(actual_roles) != len(semantics.entities):
            issues.append(_fail("duplicate_entity_role","$.visual_semantics.entities","roles must be unique"))
        for role in sorted(set(expected_roles)&set(actual_roles)):
            expected=expected_roles[role]; actual=actual_roles[role]
            if actual.kind != expected.kind or actual.dimension != expected.dimension:
                issues.append(_fail("entity_type_mismatch",f"$.visual_semantics.entities.{role}",f"expected {expected.kind}/{expected.dimension}"))
            if not _close(actual.value,expected.value):
                issues.append(_fail("entity_value_mismatch",f"$.visual_semantics.entities.{role}.value","value differs from reviewed numeric fixture"))

        expected_relations={item.name:item for item in spec.relations}
        actual_relations={item.id.rsplit(".",1)[-1]:item for item in semantics.relations}
        actual_by_id={item.id:item for item in semantics.entities}
        for name in sorted(set(expected_relations)-set(actual_relations)):
            issues.append(_fail("missing_relation","$.visual_semantics.relations",name))
        for name in sorted(set(actual_relations)-set(expected_relations)):
            issues.append(_fail("unexpected_relation","$.visual_semantics.relations",name))
        if len(actual_relations) != len(semantics.relations):
            issues.append(_fail("duplicate_relation_name","$.visual_semantics.relations","relation names must be unique"))
        for name in sorted(set(expected_relations)&set(actual_relations)):
            expected=expected_relations[name]; actual=actual_relations[name]
            source=actual_by_id.get(actual.source_ref); target=actual_by_id.get(actual.target_ref)
            if actual.kind != expected.kind or source is None or target is None or source.role != expected.source_role or target.role != expected.target_role:
                issues.append(_fail("relation_signature_mismatch",f"$.visual_semantics.relations.{name}","kind or endpoints differ"))
            expected_params=dict(expected.parameters)
            if set(actual.parameters) != set(expected_params):
                issues.append(_fail("relation_parameters_mismatch",f"$.visual_semantics.relations.{name}.parameters",f"expected {sorted(expected_params)}"))
            else:
                for key,value in expected_params.items():
                    if not _close(actual.parameters[key],value):
                        issues.append(_fail("relation_parameter_value_mismatch",f"$.visual_semantics.relations.{name}.parameters.{key}","numeric evidence differs"))

        expected_stages={item.name:item for item in spec.stages}
        actual_stages={item.id.rsplit(".",1)[-1]:item for item in semantics.stages}
        for name in sorted(set(expected_stages)-set(actual_stages)):
            issues.append(_fail("missing_stage","$.visual_semantics.stages",name))
        for name in sorted(set(actual_stages)-set(expected_stages)):
            issues.append(_fail("unexpected_stage","$.visual_semantics.stages",name))
        entity_ids={item.role:item.id for item in semantics.entities}; relation_ids={item.id.rsplit(".",1)[-1]:item.id for item in semantics.relations}
        for name in sorted(set(expected_stages)&set(actual_stages)):
            expected=expected_stages[name]; actual=actual_stages[name]
            expected_inputs=tuple(entity_ids.get(role,"") for role in expected.input_roles)
            expected_outputs=tuple(entity_ids.get(role,"") for role in expected.output_roles)
            expected_relation_refs=tuple(relation_ids.get(rel,"") for rel in expected.relation_names)
            if actual.layout != expected.layout or actual.input_entity_refs != expected_inputs or actual.output_entity_refs != expected_outputs or actual.relation_refs != expected_relation_refs:
                issues.append(_fail("stage_signature_mismatch",f"$.visual_semantics.stages.{name}","layout or evidence refs differ"))
            if actual.expected_invariants != expected.invariants:
                issues.append(_fail("stage_invariants_mismatch",f"$.visual_semantics.stages.{name}.expected_invariants",f"expected {expected.invariants}"))

        if set(actual_stages) == set(expected_stages) and len(actual_stages) != len(semantics.stages):
            issues.append(_fail("duplicate_stage_name","$.visual_semantics.stages","stage names must be unique"))
        # Always recompute when enough roles exist.  Exact fixture checks above
        # are structural; this calculation independently proves the theorem.
        if not (set(expected_roles)-set(actual_roles)):
            try:
                evidence=_mathematical_evidence(topic_id,actual_roles,semantics.relations)
                computed=set(evidence.get("invariants",{}))
                if computed != set(spec.invariants):
                    issues.append(_fail("invariant_coverage","$.visual_semantics","computed invariants do not exactly cover the topic"))
            except (KeyError,ValueError,VisualCompileError) as error:
                if isinstance(error,VisualCompileError): issues.extend(error.issues)
                else: issues.append(_fail("mathematical_invariant","$.visual_semantics",str(error)))
        return tuple(issues)

    @classmethod
    def compile(cls, *, topic_id: str, semantics: VisualSemantics, context: Any) -> Chapter4CompileResult:
        issues=cls.validate(topic_id,semantics)
        if issues:
            raise VisualCompileError(tuple(sorted(issues,key=lambda item:(item.code,item.path,item.message))))
        spec=semantic_for(topic_id); entities_by_id={item.id:item for item in semantics.entities}; by_role={item.role:item for item in semantics.entities}
        operations: list[dict[str,Any]]=[]; aliases: dict[str,tuple[str,...]]={}
        for entity in semantics.entities:
            entity_ops,entity_aliases=_entity_operations(entity,_entity_alias(entity.role),spec.scene_kind,context)
            operations.extend(_layout_operations(topic_id,entity.role,entity_ops)); aliases[entity.id]=entity_aliases
        if spec.scene_kind == "3d":
            # A three-dimensional family still needs one protocol-level geometry
            # primitive so that the scene itself is not evidenced only by
            # linear3d/plane3d helper aliases.  Choose two genuine directions
            # from the topic data; the defaults merely provide the ambient axes
            # when a topic intentionally contains only point/vector entities.
            scene_vectors: list[list[float]] = []
            for entity in semantics.entities:
                if entity.kind not in {"basis", "subspace", "matrix"}:
                    continue
                candidate_vectors = _matrix(entity.value)
                if entity.kind == "matrix":
                    candidate_vectors = [list(column) for column in zip(*candidate_vectors, strict=True)]
                scene_vectors.extend(
                    vector for vector in candidate_vectors if any(abs(component) > TOL for component in vector)
                )
            for ambient_axis in ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]):
                if len(scene_vectors) >= 2:
                    break
                scene_vectors.append(ambient_axis)
            operations.append(
                {
                    "op": "geometry.parallelogram3d",
                    "alias": "ch04__scene__parallelogram",
                    "origin": [0.0, 0.0, 0.0],
                    "vectors": scene_vectors[:2],
                    "opacity": 0.16,
                }
            )
        if topic_id == "ch04.kernel-image":
            bundle_alias="ch04__kernel_image__bundle"
            domain=_matrix(by_role["domain"].value); kernel=[_vector(by_role["kernel_direction"].value,2)]; image=_matrix(by_role["image"].value)
            operations.append({"op":"geometry.mapping_bundle","alias":bundle_alias,"dimension":2,"origin":[0.0,0.0],"offset":[0.0,0.0],"basis":domain,"bounds":_bounds(context,2),"domain_basis":domain,"kernel_basis":kernel,"image_basis":image,"rank":_rank(by_role["map_T"].value),"lanes":{"domain":{"basis":domain,"origin":[-3.0,0.0]},"kernel":{"basis":kernel,"origin":[-3.0,0.0]},"image":{"basis":image,"origin":[3.0,0.0]}}})
        for relation in semantics.relations:
            relation_ops=_relation_operations(topic_id,relation,entities_by_id,context)
            relation_ops=_layout_operations(topic_id,entities_by_id[relation.source_ref].role,relation_ops)
            operations.extend(relation_ops)
            real_aliases=tuple(str(op["alias"]) for op in relation_ops if isinstance(op.get("alias"),str) and not str(op.get("op","")).startswith("annotation."))
            if not real_aliases:
                raise VisualCompileError((_fail("annotation_only_evidence",f"$.visual_semantics.relations.{relation.id}","relation has no geometric operation"),))
            aliases[relation.id]=real_aliases
        operation_names={str(op.get("op")) for op in operations}
        missing=set(spec.expected_operations)-operation_names
        if missing:
            raise VisualCompileError(tuple(_fail("missing_expected_operation","$.operations",name) for name in sorted(missing)))
        operation_aliases={str(op.get("alias")):str(op.get("op")) for op in operations if isinstance(op.get("alias"),str)}
        for semantic_id,bound_aliases in aliases.items():
            if not bound_aliases or any(alias not in operation_aliases or operation_aliases[alias].startswith("annotation.") for alias in bound_aliases):
                raise VisualCompileError((_fail("annotation_only_evidence",f"$.aliases.{semantic_id}","semantic evidence must bind a real operation"),))
        evidence=_mathematical_evidence(topic_id,by_role,semantics.relations)
        return Chapter4CompileResult(tuple(operations),MappingProxyType(aliases),MappingProxyType(evidence))


def compile_chapter_04(topic_id: str, semantics: VisualSemantics, context: Any) -> dict[str, Any]:
    result=Chapter4FamilyCompiler.compile(topic_id=topic_id,semantics=semantics,context=context)
    return {"operations":result.operations,"aliases":result.aliases,"evidence":result.evidence}


__all__=["Chapter4CompileResult","Chapter4FamilyCompiler","compile_chapter_04"]
