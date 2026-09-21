"""Strict, computed Chapter 4 semantic family compiler."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping
from types import MappingProxyType

from linear_algebra.chapter_04_semantics import Chapter4Semantic, semantic_for
from linear_algebra.teaching.model import VisualEntity, VisualRelation, VisualSemantics
from ..compiler import CompileIssue, VisualCompileError
from ..palette import known_role, role_color

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

# 4.1.3 按对象取色，派生虚线跟随源对象。
_COL_NULL_COLORED_TOPIC = "ch04.subspace.col-null"
_COL_NULL_VECTOR_SYMBOLS: Mapping[str, str] = MappingProxyType({
    "input_vector_a": r"x_{1}",
    "output_vector_a": r"Ax_{1}",
    "input_vector_b": r"x_{2}",
    "output_vector_b": r"Ax_{2}",
    "input_vector_c": r"x_{3}",
    "output_vector_c": r"Ax_{3}",
    "kernel_vector": r"k",
})

# 4.2 的主向量分别着色，平移项沿用来源颜色。
_DEPENDENCE_COLORED_TOPIC = "ch04.dependence.redundancy"
_DEPENDENCE_ARROW_HEAD_SCALE = 2.0 / 3.0
_DEPENDENCE_GENERATOR_TOKENS: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "span_line": ("vector_a",),
    "span_plane": ("vector_a", "vector_b"),
    "independent_set": ("vector_a", "vector_b", "transformed_a"),
    "dependent_set": ("vector_a", "vector_b", "transformed_a"),
})
_DEPENDENCE_GENERATOR_SYMBOLS: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "span_line": (r"\boldsymbol{u}",),
    "span_plane": (r"\boldsymbol{u}", r"\boldsymbol{v}"),
    "independent_set": (r"\boldsymbol{u}", r"\boldsymbol{v}", r"\boldsymbol{w}"),
    "dependent_set": (r"\boldsymbol{u}", r"\boldsymbol{v}", r"\boldsymbol{w}"),
})
_DEPENDENCE_OBJECT_TOKENS: Mapping[str, str] = MappingProxyType({
    "span_line": "direction",
    "span_plane": "area",
    "dependent_set": "residual",
})

# 4.3 的颜色跟随基向量，目标向量在两个窗格中保持同色。
_BASIS_COLORED_TOPIC = "ch04.basis.definition"
_BASIS_GENERATOR_TOKENS: Mapping[str, tuple[str, str]] = MappingProxyType({
    "standard_basis": ("basis_e1", "basis_e2"),
    "oblique_basis": ("transformed_a", "transformed_b"),
})
_BASIS_OBJECT_TOKENS: Mapping[str, str] = MappingProxyType({
    "same_vector": "combination",
})

# 基向量标签与正文符号一致，便于识别当前坐标尺。
_BASIS_GENERATOR_LABELS: Mapping[str, tuple[str, str]] = MappingProxyType({
    "standard_basis": ("e_1", "e_2"),
    "oblique_basis": ("b_1", "b_2"),
})

_SUBSCRIPT_DIGITS = "₀₁₂₃₄₅₆₇₈₉"


def _subscript(index: int) -> str:
    """把序号写成 Unicode 下标：标记里写 e₁ 比写 e_1 更接近它在正文里的样子。"""
    return "".join(_SUBSCRIPT_DIGITS[int(digit)] for digit in str(index))


def _generator_label(topic_id: str, role: str, index: int, fallback: str) -> str:
    """Return the marker text for one generator direction of a basis."""
    labels = _BASIS_GENERATOR_LABELS.get(role) if topic_id == _BASIS_COLORED_TOPIC else None
    if labels is not None and index <= len(labels):
        return labels[index - 1]
    return f"{fallback}{_subscript(index)}" if fallback else ""


def _basis_generator_colors(topic_id: str, role: str) -> tuple[str, ...]:
    """Return one palette color per generator of the named basis (empty elsewhere)."""
    if topic_id == _BASIS_COLORED_TOPIC:
        tokens = _BASIS_GENERATOR_TOKENS.get(role)
    elif topic_id == _DEPENDENCE_COLORED_TOPIC:
        tokens = _DEPENDENCE_GENERATOR_TOKENS.get(role)
    else:
        return ()
    return tuple(role_color(token) for token in tokens) if tokens else ()


def _basis_generator_labels(topic_id: str, role: str) -> tuple[str, ...]:
    """Return one marker text per generator of the named basis (empty elsewhere)."""
    if topic_id != _BASIS_COLORED_TOPIC:
        return ()
    return _BASIS_GENERATOR_LABELS.get(role, ())


@dataclass(frozen=True)
class _SubspaceLook:
    """How one topic draws a subspace itself (plane for rank 2, line for rank 1).

    ``line_marks`` are the intervals (in units of the direction vector) drawn as
    segments; the default is one centred segment through the origin.
    """

    plane_size: float
    plane_opacity: float
    line_marks: tuple[tuple[float, float], ...] = ((-2.0, 2.0),)
    line_style: str = "solid"


_DEFAULT_LOOK = _SubspaceLook(2.5, 0.2)
_LOOKS: Mapping[str, _SubspaceLook] = MappingProxyType({
    # 平面覆盖全部采样落点，零空间用向量外侧虚线表示延伸。
    # 降低平面透明度，避免遮住落在其上的输出向量。
    "ch04.subspace.col-null": _SubspaceLook(5.0, 0.08, ((3.3, 4.2), (-3.8, -2.9)), "dashed"),
})


def _look(topic_id: str) -> _SubspaceLook:
    return _LOOKS.get(topic_id, _DEFAULT_LOOK)


def _object_color(topic_id: str, role: str) -> str | None:
    """Return the topic-local object color, or None to keep renderer defaults."""
    if topic_id == _BASIS_COLORED_TOPIC:
        token = _BASIS_OBJECT_TOKENS.get(role)
        return role_color(token) if token is not None else None
    if topic_id == _DEPENDENCE_COLORED_TOPIC:
        token = _DEPENDENCE_OBJECT_TOKENS.get(role)
        return role_color(token) if token is not None else None
    if topic_id != _COL_NULL_COLORED_TOPIC or not known_role(role):
        return None
    return role_color(role)


# 场景标签按舞台注册别名；纯文本下标由渲染层转换为 Unicode。
_COL_NULL_STAGE_LABELS: Mapping[str, tuple[tuple[str, str, tuple[float, float, float], str], ...]] = MappingProxyType({
    "stage.ch04.subspace.col-null.column_space": (
        ("col_space", "Col(A)", (-2.35, -2.35, 0.12), "column_space"),
        # 向量名放在箭杆旁，箭头尖端留作端点标记。
        ("input_a", "x_1", (1.05, 0.57, 1.65), "input_vector_a"),
        ("output_a", "Ax_1", (1.05, 0.60, 0.12), "output_vector_a"),
        ("input_b", "x_2", (-1.10, 0.60, 1.10), "input_vector_b"),
        ("output_b", "Ax_2", (-1.10, 0.60, 0.12), "output_vector_b"),
        ("input_c", "x_3", (-0.66, -1.14, -1.00), "input_vector_c"),
        ("output_c", "Ax_3", (-0.64, -1.15, 0.12), "output_vector_c"),
    ),
    "stage.ch04.subspace.col-null.null_space": (
        ("col_space", "Col(A)", (-2.35, -2.35, 0.12), "column_space"),
        ("null_space", "Null(A)", (0.18, 0.18, 4.35), "null_space"),
        ("kernel", "k", (0.16, 0.16, 1.58), "kernel_vector"),
        ("zero", "0", (0.16, 0.16, 0.16), "zero"),
    ),
})


def _col_null_label_operations(stage_id: str) -> list[dict[str, Any]]:
    """Return only the labels that belong to one confirmed 4.1 case pane."""

    return [
        {
            "op": "annotation.formula",
            "alias": f"ch04__annotation__{stage_id.rsplit('.', 1)[-1]}__{name}",
            "text": text,
            "position": list(position),
            "color": _object_color(_COL_NULL_COLORED_TOPIC, role),
        }
        for name, text, position, role in _COL_NULL_STAGE_LABELS.get(stage_id, ())
    ]


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
    return operations


def _normal(basis: list[list[float]]) -> list[float]:
    result = _cross(basis[0], basis[1])
    if math.sqrt(sum(v*v for v in result)) <= TOL:
        raise ValueError("plane basis is dependent")
    return result


def _entity_operations(entity: VisualEntity, alias: str, scene: str, context: Any, topic_id: str = "") -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    ops: list[dict[str, Any]] = []
    if scene == "2d":
        color = _object_color(topic_id, entity.role)
        if entity.kind == "point":
            ops.append({"op":"point.upsert","alias":alias,"coordinates":_vector(entity.value,2),"name":entity.label})
        elif entity.kind == "vector":
            origin=f"{alias}__origin"; end=f"{alias}__end"
            ops.extend(({"op":"point.upsert","alias":origin,"coordinates":[0.0,0.0],"name":"O"}, {"op":"point.upsert","alias":end,"coordinates":_vector(entity.value,2),"name":entity.label}, {"op":"linear.upsert","alias":alias,"start":origin,"end":end,"kind":"vector","role":"primary",**_color_kwargs(color)}))
        elif entity.kind == "matrix":
            ops.append({"op":"geometry.transformed_grid","alias":alias,"matrix":_matrix(entity.value),"bounds":_bounds(context,2),"step":1.0})
        elif entity.kind in {"basis","subspace","region"}:
            basis=_matrix(entity.value)
            if entity.role in {"standard_basis", "oblique_basis"}:
                basis=[list(column) for column in zip(*basis)]
            ops.append({"op":"geometry.subspace_region","alias":alias,"basis":basis[:2],"bounds":_bounds(context,2),"opacity":0.2})
            # 区域协议只接收两个方向，因此生成元需分别绘制并独立着色。
            if entity.kind == "basis":
                generator_colors=_basis_generator_colors(topic_id, entity.role)
                for index, vector in enumerate(basis, 1):
                    tone=generator_colors[index-1] if index <= len(generator_colors) else None
                    mark=_generator_label(topic_id, entity.role, index, entity.label)
                    ops.extend(_vector_relation(f"{alias}__generator_{index}",vector,tone,mark))
        elif entity.kind == "affine_set":
            ops.append({"op":"geometry.subspace_region","alias":alias,"basis":[[1.0,0.0],[0.0,1.0]],"origin":_vector(entity.value,2),"bounds":_bounds(context,2),"opacity":0.16})
        elif entity.kind == "constraint":
            ops.append({"op":"curve.create","alias":alias,"kind":"explicit","expression":"y=x^2"})
        else:
            raise ValueError(f"unsupported 2d entity kind {entity.kind}")
        if topic_id == _BASIS_COLORED_TOPIC:
            return ops, tuple(
                str(operation["alias"])
                for operation in ops
                if isinstance(operation.get("alias"), str)
            )
        return ops, (alias,)

    color = _object_color(topic_id, entity.role)
    if entity.kind == "point":
        ops.append({"op":"point3d.upsert","alias":alias,"coordinates":_vector(entity.value,3),"name":entity.label})
        return ops, (alias,)
    if entity.kind == "vector":
        vector=_vector(entity.value,3)
        if any(abs(v)>TOL for v in vector):
            ops.append({
                "op":"linear3d.upsert",
                "alias":alias,
                "start":[0.0,0.0,0.0],
                "end":vector,
                "kind":"vector",
                "role":"primary",
                **_color_kwargs(color),
                **_vector_rendering(topic_id, entity.role),
            })
        else:
            ops.append({"op":"point3d.upsert","alias":alias,"coordinates":vector,"name":entity.label})
        return ops, (alias,)
    if entity.kind == "affine_set":
        basis=_matrix(entity.value)
        ops.append({"op":"plane3d.upsert","alias":alias,"origin":basis[-1],"normal":_normal(basis[:2]),"size":2.5,"opacity":0.2,**_color_kwargs(color)})
        return ops, (alias,)
    if entity.kind in {"matrix","basis","subspace","region"}:
        vectors=_matrix(entity.value)
        if entity.kind == "matrix":
            vectors=[list(column) for column in zip(*vectors)]
        rank=_rank(vectors)
        look=_look(topic_id)
        if rank == 2:
            algebra_kwargs = (
                {"algebra_visible": True, "algebra_label": entity.label}
                if topic_id == _COL_NULL_COLORED_TOPIC and entity.role == "column_space"
                else {}
            )
            ops.append({"op":"plane3d.upsert","alias":alias,"origin":[0.0,0.0,0.0],"normal":_normal(vectors),"size":look.plane_size,"opacity":look.plane_opacity,**_color_kwargs(color),**algebra_kwargs})
            aliases=[alias]
            generator_colors=_basis_generator_colors(topic_id, entity.role)
            if entity.kind == "basis" and generator_colors:
                for index, vector in enumerate(vectors, 1):
                    generator_alias=f"{alias}__generator_{index}"
                    tone=generator_colors[index-1] if index <= len(generator_colors) else None
                    symbol=_generator_symbol(topic_id, entity.role, index)
                    ops.append({
                        "op":"linear3d.upsert", "alias":generator_alias,
                        "start":[0.0,0.0,0.0], "end":vector,
                        "kind":"vector", "role":"primary",
                        **_color_kwargs(tone),
                        **_vector_rendering(topic_id, entity.role, index),
                        **({"algebra_symbol": symbol} if symbol else {}),
                    })
                    aliases.append(generator_alias)
            return ops, tuple(aliases)
        if rank == 1:
            vector=next(v for v in vectors if any(abs(x)>TOL for x in v))
            style_kwargs=_color_kwargs(color)
            if look.line_style != "solid":
                style_kwargs["style"]=look.line_style
            aliases=[]
            for index,(from_units,to_units) in enumerate(look.line_marks,1):
                mark_alias=alias if index==1 else f"{alias}__extent_{index}"
                ops.append({"op":"linear3d.upsert","alias":mark_alias,"start":_scale(vector,from_units),"end":_scale(vector,to_units),"kind":"segment","role":"primary",**style_kwargs})
                aliases.append(mark_alias)
            if entity.kind == "basis":
                generator_alias=f"{alias}__generator_1"
                tone=(_basis_generator_colors(topic_id, entity.role) or (color,))[0]
                symbol=_generator_symbol(topic_id, entity.role, 1)
                ops.append({
                    "op":"linear3d.upsert", "alias":generator_alias,
                    "start":[0.0,0.0,0.0], "end":vector,
                    "kind":"vector", "role":"primary",
                    **_color_kwargs(tone),
                    **_vector_rendering(topic_id, entity.role, 1),
                    **({"algebra_symbol": symbol} if symbol else {}),
                })
                aliases.append(generator_alias)
            return ops, tuple(aliases)
        aliases=[]
        generator_colors=_basis_generator_colors(topic_id, entity.role)
        for index, vector in enumerate(vectors[:3], 1):
            axis=f"{alias}__axis_{index}"; aliases.append(axis)
            if any(abs(x)>TOL for x in vector):
                tone=generator_colors[index-1] if index <= len(generator_colors) else color
                symbol=_generator_symbol(topic_id, entity.role, index)
                ops.append({
                    "op":"linear3d.upsert", "alias":axis,
                    "start":[0.0,0.0,0.0], "end":vector,
                    "kind":"vector", "role":"primary",
                    **_color_kwargs(tone),
                    **_vector_rendering(topic_id, entity.role, index),
                    **({"algebra_symbol": symbol} if symbol else {}),
                })
            else:
                ops.append({"op":"point3d.upsert","alias":axis,"coordinates":[0.0,0.0,0.0],"name":"0"})
        return ops, tuple(aliases)
    raise ValueError(f"unsupported 3d entity kind {entity.kind}")


def _color_kwargs(color: str | None) -> dict[str, Any]:
    """Only override the renderer color when the topic declares an object color."""
    return {} if color is None else {"color": color}


def _generator_symbol(topic_id: str, role: str, index: int) -> str:
    if topic_id != _DEPENDENCE_COLORED_TOPIC:
        return ""
    symbols = _DEPENDENCE_GENERATOR_SYMBOLS.get(role, ())
    return symbols[index - 1] if index <= len(symbols) else ""


def _vector_rendering(topic_id: str, role: str, index: int | None = None) -> dict[str, object]:
    """Return topic-local display metadata for 3D vectors."""

    if topic_id == _COL_NULL_COLORED_TOPIC:
        rendering: dict[str, object] = {}
        symbol = _COL_NULL_VECTOR_SYMBOLS.get(role)
        if symbol is not None:
            rendering["algebra_symbol"] = symbol
        return rendering
    if topic_id == _DEPENDENCE_COLORED_TOPIC:
        # 4.2 的单位向量在四窗格里较短；缩小头部后，其视觉比例与 4.1 的
        # 较长采样向量一致。关系项只是组合过程，不是独立的代数区对象。
        rendering: dict[str, object] = {
            "arrow_head_scale": _DEPENDENCE_ARROW_HEAD_SCALE,
            "algebra_visible": index is not None,
        }
        if index is not None:
            symbol = _generator_symbol(topic_id, role, index)
            if symbol:
                rendering["algebra_symbol"] = symbol
        return rendering
    return {}


def _parameters(relation: VisualRelation) -> Mapping[str, object]:
    return relation.parameters


def _vector_relation(alias: str, endpoint: object, color: str | None = None, label: str = "") -> list[dict[str, Any]]:
    origin=f"{alias}__origin"; end=f"{alias}__end"
    # 仅为计划中有名称的向量绘制端点标记。
    return [{"op":"point.upsert","alias":origin,"coordinates":[0.0,0.0],"name":"O"},
            {"op":"point.upsert","alias":end,"coordinates":_vector(endpoint,2),"name":label},
            {"op":"linear.upsert","alias":alias,"start":origin,"end":end,"kind":"vector","role":"result",**_color_kwargs(color)}]


def _linear_map_case_operations(
    alias: str, parameters: Mapping[str, object], context: Any, *, translation: bool
) -> list[dict[str, Any]]:
    """Draw one complete 4.4 witness from the same values used by its checks."""

    if translation:
        matrix = [[1.0, 0.0], [0.0, 1.0]]
        origin = _vector(parameters["shift"], 2)
        direct = _vector(parameters["sum_image"], 2)
        separate = _vector(parameters["sum_of_images"], 2)
        image_u = _vector(parameters["image_u"], 2)
        image_v = _vector(parameters["image_v"], 2)
        vectors = (
            ("image_u", image_u, role_color("vector_a"), "T(u)"),
            ("image_v", image_v, role_color("vector_b"), "T(v)"),
            ("direct", direct, role_color("combination"), "T(u+v)"),
            ("separate", separate, role_color("transformed_b"), "T(u)+T(v)"),
        )
        polygon = [
            [0.0, 0.0],
            image_u,
            separate,
            image_v,
        ]
        grid_color = role_color("neutral")
    else:
        matrix = _matrix(parameters["matrix"])
        origin = [0.0, 0.0]
        image_u = _vector(parameters["image_u"], 2)
        image_v = _vector(parameters["image_v"], 2)
        sum_image = _vector(parameters["sum_image"], 2)
        scaled_image = _vector(parameters["scaled_image"], 2)
        vectors = (
            ("image_u", image_u, role_color("vector_a"), "T(u)"),
            ("image_v", image_v, role_color("vector_b"), "T(v)"),
            ("sum", sum_image, role_color("combination"), "T(u+v)"),
            ("scaled", scaled_image, role_color("transformed_b"), "T(2u)"),
        )
        polygon = [
            [0.0, 0.0],
            image_u,
            sum_image,
            image_v,
        ]
        grid_color = role_color("transformed_a")

    operations: list[dict[str, Any]] = [
        {
            "op": "geometry.transformed_grid",
            "alias": f"{alias}__grid",
            "matrix": matrix,
            "bounds": _bounds(context, 2),
            "step": 1.0,
            "origin": origin,
            "color": grid_color,
            "show_source_grid": False,
        },
        {
            "op": "geometry.polygon",
            "alias": f"{alias}__parallelogram",
            "vertices": polygon,
            "opacity": 0.1,
            "outline": True,
            "color": role_color("construction"),
        },
    ]
    for name, endpoint, color, label in vectors:
        operations.extend(_vector_relation(f"{alias}__{name}", endpoint, color, label))
    return operations


def _coordinate_operation(alias: str, basis: object, coordinates: object, vector: object, context: Any) -> dict[str, Any]:
    return {"op":"geometry.coordinate_readout","alias":alias,"basis_matrix":_matrix(basis),
            "standard_vector":_vector(vector,2),"alternate_coordinates":_vector(coordinates,2),
            "bounds":_bounds(context,2),"tolerance":TOL,"basis_alias":f"{alias}__basis",
            "standard_alias":f"{alias}__standard","alternate_alias":f"{alias}__alternate",
            "entity_count":4,"sample_count":4}


def _coefficient_text(value: float) -> str:
    """把系数写成窗格里能读的样子：整数不拖小数点。"""
    return str(int(round(value))) if abs(value - round(value)) <= TOL else f"{value:.4g}"


def _coordinate_operations(alias: str, basis: object, coordinates: object, vector: object, context: Any,
                           basis_colors: tuple[str, ...] = (), basis_labels: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """Draw one readout: its grid and each component arrow follow the basis being used.

    两条分量箭头是这个案例真正要讲的东西——它们把「读数」拆成「每根基各走了多少」。
    所以标记写在箭头上（5e₁、3e₂ 这样的项），拐点只是几何端点，不带标记。
    """
    readout=_coordinate_operation(alias,basis,coordinates,vector,context)
    grid={**readout,"op":"geometry.basis_grid","alias":f"{alias}__grid","bounds":[-5.0,5.0,-5.0,5.0],**_color_kwargs(basis_colors[0] if basis_colors else None)}
    operations=[grid,readout]
    endpoint=[0.0,0.0]
    for index,(column,coefficient) in enumerate(zip(zip(*_matrix(basis)),_vector(coordinates)),1):
        next_endpoint=_add(endpoint,_scale(column,coefficient))
        term=f"{alias}__component_{index}"
        tone=basis_colors[index-1] if index <= len(basis_colors) else None
        symbol=basis_labels[index-1] if index <= len(basis_labels) else ""
        mark=f"{_coefficient_text(coefficient)}{symbol}" if symbol else ""
        operations.extend([
            {"op":"point.upsert","alias":f"{term}__start","coordinates":endpoint},
            {"op":"point.upsert","alias":f"{term}__end","coordinates":next_endpoint},
            {"op":"linear.upsert","alias":term,"start":f"{term}__start","end":f"{term}__end","kind":"vector","role":"result",
             "label":mark,**_color_kwargs(tone)},
        ])
        endpoint=next_endpoint
    return operations


def _relation_operations(topic_id: str, relation: VisualRelation, entities: Mapping[str, VisualEntity], context: Any) -> list[dict[str, Any]]:
    alias=_relation_alias(relation.id.rsplit(".",1)[-1]); p=_parameters(relation)
    source=entities[relation.source_ref]; target=entities[relation.target_ref]
    if source.dimension == 2:
        if topic_id == "ch04.linear-map.definition" and relation.id.endswith(".stretch_case"):
            return _linear_map_case_operations(alias, p, context, translation=False)
        if topic_id == "ch04.linear-map.definition" and relation.id.endswith(".translation_case"):
            return _linear_map_case_operations(alias, p, context, translation=True)
        if relation.kind == "coordinate_equivalence":
            # 坐标读数的网格和分量箭头沿用对应基的颜色。
            return _coordinate_operations(alias,p["basis_matrix"],p["coordinates"],p["expected_vector"],context,
                                          _basis_generator_colors(topic_id, source.role),
                                          _basis_generator_labels(topic_id, source.role))
        if relation.kind == "same_measure":
            spec=semantic_for(topic_id); by_role={e.role:e for e in entities.values()}
            basis=by_role["oblique_basis"].value; coords=by_role["oblique_coordinates"].value; vector=by_role["same_vector"].value
            return _coordinate_operations(alias,basis,coords,vector,context)
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
            return _vector_relation(alias,target.value,label=target.label)
        if relation.kind == "not_linear":
            if source.kind == "constraint": return [{"op":"curve.create","alias":alias,"kind":"explicit","expression":"y=x^2"}]
            return _vector_relation(alias,p["origin_image"])
        if relation.kind == "basis_of" or (relation.kind in {"dimension_of","linear_dependence","contains"} and source.kind in {"basis","subspace"}):
            return _entity_operations(source,alias,"2d",context,topic_id)[0]
        # 关系别名下重绘目标，用作类型关系的几何证据。
        return _entity_operations(target,alias,"2d",context,topic_id)[0]

    if topic_id == "ch04.subspace.col-null" and relation.kind == "maps_to":
        # 4.1.3 的映射只补源到目标的虚线，不重复绘制目标。
        start = _vector(source.value, 3)
        end = _vector(target.value, 3)
        if all(abs(value) <= TOL for value in end):
            # 映射到原点时只绘制像点，省略与源向量重合的连线。
            return [{"op": "point3d.upsert", "alias": alias, "coordinates": end, "name": target.label}]
        return [
            {
                "op": "linear3d.upsert",
                "alias": alias,
                "start": start,
                "end": end,
                "kind": "segment",
                "role": "construction",
                "style": "dashed",
                "color": _object_color(topic_id, source.role) or role_color("construction"),
            }
        ]
    if relation.kind == "intersects_in":
        return [{"op":"geometry.intersection","alias":alias,"first":_primary_entity_alias(source.role,source),"second":_primary_entity_alias(target.role,target)}]
    if relation.kind == "linear_combination":
        coefficients = (
            [float(p["coefficient"])]
            if "coefficient" in p
            else _vector(p["coefficients"])
        )
        vectors=[_scale(vector,coefficient) for vector,coefficient in zip(_matrix(source.value),coefficients)]
        if topic_id == _DEPENDENCE_COLORED_TOPIC:
            # 4.2 的窗格只用生成向量说明张成空间；组合过程保留为落点，
            # 避免额外箭头与代数区列出的 u、v、w 数量不一致。
            endpoint=[0.0,0.0,0.0]
            for vector in vectors:
                endpoint=_add(endpoint,vector)
            return [{"op":"point3d.upsert","alias":alias,"coordinates":endpoint,"name":target.label}]
        operations=[]; endpoint=[0.0,0.0,0.0]
        generator_colors=_basis_generator_colors(topic_id, source.role)
        for index,vector in enumerate(vectors,1):
            end=_add(endpoint,vector)
            tone=generator_colors[index-1] if index <= len(generator_colors) else None
            operations.append({
                "op":"linear3d.upsert", "alias":f"{alias}__term_{index}",
                "start":endpoint, "end":end, "kind":"vector", "role":"result",
                **_color_kwargs(tone),
                **_vector_rendering(topic_id, source.role),
            })
            endpoint=end
        # 组合落点使用数学标签“0”，不显示内部关系名称。
        operations.append({"op":"point3d.upsert","alias":alias,"coordinates":endpoint,"name":target.label})
        return operations
    if relation.kind in {"union_counterexample","linear_combination","sum"}:
        if relation.kind == "union_counterexample":
            by_role={e.role:e for e in entities.values()}; vectors=[_vector(by_role["union_u"].value,3),_vector(by_role["union_v"].value,3)]
        else:
            vectors=_matrix(source.value)[:2] if source.kind in {"basis","matrix"} else [_vector(source.value,3),_vector(p.get("other_vector"),3)]
        return [{"op":"geometry.parallelogram3d","alias":alias,"origin":[0.0,0.0,0.0],"vectors":vectors,"opacity":0.16}]
    if relation.kind == "affine_translation":
        basis=_matrix(source.value)
        return [{"op":"plane3d.upsert","alias":alias,"origin":_vector(p["offset"],3),"normal":_normal(basis),"size":2.5,"opacity":0.16}]
    return _entity_operations(target,alias,"3d",context,topic_id)[0]


def _mathematical_evidence(topic_id: str, by_role: Mapping[str, VisualEntity], relations: tuple[VisualRelation, ...] = ()) -> dict[str, object]:
    """Recompute the advertised theorem from entity values, not labels."""
    value=lambda role: by_role[role].value
    checks: dict[str,bool] = {}
    numbers: dict[str,object] = {}
    parameters={relation.id.rsplit(".",1)[-1]:relation.parameters for relation in relations}
    if topic_id == "ch04.subspace.col-null":
        # 矩阵只作为关系参数；实体和关系中的采样向量必须一致。
        matrix=_matrix(parameters["projection_a"]["matrix"])
        checks["diag_1_1_0"]=_close(matrix,[[1,0,0],[0,1,0],[0,0,0]])
        null_basis=_matrix(value("null_space"))
        kernel=_vector(value("kernel_vector"),3)
        kernel_sample=_vector(parameters["collapse"]["input_vector"],3)
        checks["kernel_to_zero"]=(
            _close(kernel,kernel_sample)
            and _close(_matvec(matrix,kernel),[0,0,0])
            and _in_span(null_basis,kernel)
        )
        columns=[list(column) for column in zip(*matrix)]
        image_basis=_matrix(value("column_space"))
        names=("a","b","c")
        samples={name:_vector(value(f"input_vector_{name}"),3) for name in names}
        parameter_samples={name:_vector(parameters[f"projection_{name}"]["input_vector"],3) for name in names}
        images={name:_matvec(matrix,sample) for name,sample in samples.items()}
        checks["image_xy_plane"]=(
            _rank(image_basis)==_rank(columns)==2 and _same_span(image_basis,columns)
            and all(_close(samples[name],parameter_samples[name]) for name in names)
            and all(_close(image,value(f"output_vector_{name}")) for name,image in images.items())
            and all(_in_span(image_basis,image) for image in images.values())
        )
        numbers.update(columns=columns,images=images,image_rank=_rank(columns))
    elif topic_id == "ch04.dependence.redundancy":
        line=_matrix(value("span_line"))
        plane=_matrix(value("span_plane"))
        independent=_matrix(value("independent_set"))
        dependent=_matrix(value("dependent_set"))
        line_parameters=parameters["line_combination"]
        plane_parameters=parameters["plane_combination"]
        independent_parameters=parameters["independent_combination"]
        dependent_parameters=parameters["dependent_combination"]
        line_combination=_combination(line,[float(line_parameters["coefficient"])])
        plane_combination=_combination(plane,_vector(plane_parameters["coefficients"]))
        independent_coefficients=_vector(independent_parameters["coefficients"])
        dependent_coefficients=_vector(dependent_parameters["coefficients"])
        independent_combination=_combination(independent, independent_coefficients)
        dependent_combination=_combination(dependent, dependent_coefficients)
        numbers.update(
            line_rank=_rank(line),
            plane_rank=_rank(plane),
            independent_rank=_rank(independent),
            dependent_rank=_rank(dependent),
            line_combination=line_combination,
            plane_combination=plane_combination,
            independent_combination=independent_combination,
            dependent_combination=dependent_combination,
        )
        checks["line_span_1d"] = (
            _rank(line) == 1
            and _close(line_combination, value("line_sample"))
            and _close(line_combination, line_parameters["expected_result"])
        )
        checks["plane_span_2d"] = (
            _rank(plane) == 2
            and all(abs(component) <= TOL for component in plane_combination[2:])
            and _close(plane_combination, value("plane_sample"))
            and _close(plane_combination, plane_parameters["expected_result"])
        )
        checks["independent_only_zero_solution"] = _rank(independent) == 3
        checks["independent_span_r3"] = (
            _rank(independent) == 3
            and _close(independent_combination, value("independent_sample"))
            and _close(independent_combination, independent_parameters["expected_result"])
        )
        checks["dependent_nonzero_combination_zero"] = (
            _close(dependent_combination, [0, 0, 0])
            and _close(dependent_combination, dependent_parameters["expected_result"])
            and any(abs(value) > TOL for value in dependent_coefficients)
        )
        checks["dependent_coplanar"] = _rank(dependent) == 2
    elif topic_id == "ch04.basis.definition":
        # 基必须秩为 2、张成 R²，且关系参数需与实体值一致。
        standard_matrix=_matrix(value("standard_basis"))
        oblique_matrix=_matrix(value("oblique_basis"))
        oblique_columns=[list(column) for column in zip(*oblique_matrix)]
        standard_columns=[list(column) for column in zip(*standard_matrix)]
        standard_parameters=parameters["standard_readout"]; oblique_parameters=parameters["oblique_readout"]
        standard_readout=_matvec(standard_parameters["basis_matrix"],standard_parameters["coordinates"])
        oblique_readout=_matvec(oblique_parameters["basis_matrix"],oblique_parameters["coordinates"])
        numbers.update(oblique_columns=oblique_columns,standard_readout=standard_readout,oblique_readout=oblique_readout)
        checks["basis_independent_and_spanning"]=(
            _rank(oblique_columns)==2
            and _same_span(oblique_columns,standard_columns)
            and _same_span(oblique_columns,standard_matrix)
        )
        checks["standard_reconstruction"]=(
            _close(standard_readout,value("same_vector"))
            and _close(_matrix(standard_parameters["basis_matrix"]),standard_matrix)
            and _close(standard_parameters["expected_vector"],value("same_vector"))
        )
        checks["coordinate_reconstruction"]=(
            _close(oblique_readout,value("same_vector"))
            and _close(_matrix(oblique_parameters["basis_matrix"]),oblique_matrix)
            and _close(oblique_parameters["expected_vector"],value("same_vector"))
        )
    elif topic_id == "ch04.linear-map.definition":
        stretch=parameters["stretch_case"]
        matrix=_matrix(value("stretch_map"))
        u=_vector(stretch["u"],2); v=_vector(stretch["v"],2)
        image_u=_matvec(matrix,u); image_v=_matvec(matrix,v)
        sum_image=_matvec(matrix,_add(u,v))
        scalar=float(stretch["scalar"])
        scaled_image=_matvec(matrix,_scale(u,scalar))
        checks["stretch_additivity"]=(
            _close(matrix,stretch["matrix"])
            and _close(image_u,stretch["image_u"])
            and _close(image_v,stretch["image_v"])
            and _close(sum_image,_add(image_u,image_v))
            and _close(sum_image,stretch["sum_image"])
            and _close(_add(image_u,image_v),stretch["sum_of_images"])
            and _close(sum_image,value("stretch_result"))
        )
        checks["stretch_homogeneity"]=(
            _close(scaled_image,_scale(image_u,scalar))
            and _close(scaled_image,stretch["scaled_image"])
            and _close(_scale(image_u,scalar),stretch["scaled_output"])
        )

        translation=parameters["translation_case"]
        shift=_vector(value("translation_shift"),2)
        translation_u=_vector(translation["u"],2)
        translation_v=_vector(translation["v"],2)
        translate=lambda vector: _add(vector,shift)
        translated_u=translate(translation_u)
        translated_v=translate(translation_v)
        translated_sum=translate(_add(translation_u,translation_v))
        separate_sum=_add(translated_u,translated_v)
        checks["translation_not_additive"]=(
            _close(shift,translation["shift"])
            and _close(translated_u,translation["image_u"])
            and _close(translated_v,translation["image_v"])
            and _close(translated_sum,translation["sum_image"])
            and _close(separate_sum,translation["sum_of_images"])
            and _close(translated_sum,value("translation_result"))
            and not _close(translated_sum,separate_sum)
        )
        numbers.update(
            stretch_sum_image=sum_image,
            stretch_scaled_image=scaled_image,
            translation_sum_image=translated_sum,
            translation_sum_of_images=separate_sum,
        )
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
        # 角色齐全时独立复算定理，夹具检查只负责结构。
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
            entity_ops,entity_aliases=_entity_operations(entity,_entity_alias(entity.role),spec.scene_kind,context,topic_id)
            operations.extend(_layout_operations(topic_id,entity.role,entity_ops)); aliases[entity.id]=entity_aliases
        if spec.scene_kind == "3d":
            # 三维族仍需一个协议级几何图元，方向优先取主题数据。
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
            if topic_id in {_COL_NULL_COLORED_TOPIC, _DEPENDENCE_COLORED_TOPIC}:
                # 4.1.3 和 4.2 隐藏与主题平面重合的脚手架方格。
                aliases["ch04__scene__parallelogram"] = ("ch04__scene__parallelogram",)
        for relation in semantics.relations:
            relation_ops=_relation_operations(topic_id,relation,entities_by_id,context)
            relation_ops=_layout_operations(topic_id,entities_by_id[relation.source_ref].role,relation_ops)
            operations.extend(relation_ops)
            real_aliases=tuple(str(op["alias"]) for op in relation_ops if isinstance(op.get("alias"),str) and not str(op.get("op","")).startswith("annotation."))
            if not real_aliases:
                raise VisualCompileError((_fail("annotation_only_evidence",f"$.visual_semantics.relations.{relation.id}","relation has no geometric operation"),))
            aliases[relation.id]=real_aliases
        if topic_id == _COL_NULL_COLORED_TOPIC:
            for stage in semantics.stages:
                label_operations = _col_null_label_operations(stage.id)
                operations.extend(label_operations)
                aliases[stage.id] = tuple(str(operation["alias"]) for operation in label_operations)
        operation_names={str(op.get("op")) for op in operations}
        missing=set(spec.expected_operations)-operation_names
        if missing:
            raise VisualCompileError(tuple(_fail("missing_expected_operation","$.operations",name) for name in sorted(missing)))
        operation_aliases={str(op.get("alias")):str(op.get("op")) for op in operations if isinstance(op.get("alias"),str)}
        stage_ids = {stage.id for stage in semantics.stages}
        for semantic_id,bound_aliases in aliases.items():
            if semantic_id in stage_ids:
                continue
            if not bound_aliases or any(alias not in operation_aliases or operation_aliases[alias].startswith("annotation.") for alias in bound_aliases):
                raise VisualCompileError((_fail("annotation_only_evidence",f"$.aliases.{semantic_id}","semantic evidence must bind a real operation"),))
        evidence=_mathematical_evidence(topic_id,by_role,semantics.relations)
        return Chapter4CompileResult(tuple(operations),MappingProxyType(aliases),MappingProxyType(evidence))


def compile_chapter_04(topic_id: str, semantics: VisualSemantics, context: Any) -> dict[str, Any]:
    result=Chapter4FamilyCompiler.compile(topic_id=topic_id,semantics=semantics,context=context)
    return {"operations":result.operations,"aliases":result.aliases,"evidence":result.evidence}


__all__=["Chapter4CompileResult","Chapter4FamilyCompiler","compile_chapter_04"]
