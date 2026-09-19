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

# 4.1.3 的取色：颜色归属于对象（那张平面、那条直线、每个向量和原点各自一种颜色），
# 由对象派生的虚线跟随源对象取色。颜色值本身只来自共享调色板，这里只决定哪些主题
# 按对象取色；其他主题继续沿用渲染器默认色。
_COL_NULL_COLORED_TOPIC = "ch04.subspace.col-null"
_COL_NULL_VECTOR_SYMBOLS: Mapping[str, str] = MappingProxyType({
    "input_vector_a": r"\boldsymbol{x}_{1}",
    "output_vector_a": r"\boldsymbol{A}\boldsymbol{x}_{1}",
    "input_vector_b": r"\boldsymbol{x}_{2}",
    "output_vector_b": r"\boldsymbol{A}\boldsymbol{x}_{2}",
    "input_vector_c": r"\boldsymbol{x}_{3}",
    "output_vector_c": r"\boldsymbol{A}\boldsymbol{x}_{3}",
    "kernel_vector": r"\boldsymbol{k}",
})

# 4.2 的两窗格都以“向量组”为主角。三根主向量分别着色，相关组里由它们平移得到的
# 三个加法项沿用同一颜色；箭头头部使用固定像素大小，不随向量长度产生大小不一的错觉。
_DEPENDENCE_COLORED_TOPIC = "ch04.dependence.redundancy"
_DEPENDENCE_GENERATOR_TOKENS: Mapping[str, tuple[str, str, str]] = MappingProxyType({
    "independent_set": ("vector_a", "vector_b", "transformed_a"),
    "dependent_set": ("vector_a", "vector_b", "transformed_a"),
})
_DEPENDENCE_GENERATOR_SYMBOLS: Mapping[str, tuple[str, str, str]] = MappingProxyType({
    "independent_set": (r"\boldsymbol{e}_1", r"\boldsymbol{e}_2", r"\boldsymbol{e}_3"),
    "dependent_set": (r"\boldsymbol{u}", r"\boldsymbol{v}", r"\boldsymbol{w}"),
})
_DEPENDENCE_OBJECT_TOKENS: Mapping[str, str] = MappingProxyType({
    "dependent_set": "residual",
})

# 4.3「基与维数」的取色：两个窗格画的是同一个点、同一个向量，能区分的只有「尺子」。
# 所以颜色跟着尺子走：标准基两根方向蓝/橙，新基两根方向紫/红；被量的那个向量自己在
# 两窗格里都是青绿——它是唯一不动的东西，颜色也必须一直不变。读数（分量箭头、基网格）
# 由它正在用的那组基派生，跟随源尺子的颜色，这正是这个案例的看点。
_BASIS_COLORED_TOPIC = "ch04.basis.definition"
_BASIS_GENERATOR_TOKENS: Mapping[str, tuple[str, str]] = MappingProxyType({
    "standard_basis": ("basis_e1", "basis_e2"),
    "oblique_basis": ("transformed_a", "transformed_b"),
})
_BASIS_OBJECT_TOKENS: Mapping[str, str] = MappingProxyType({
    "same_vector": "combination",
})

# 两组基各自的两根方向尺子，窗格标记直接写它们自己的名字，和正文写法一致
# （正文写 $\boldsymbol e_1$、$\boldsymbol b_1$，标记就写 e₁、b₁）。用户不用认颜色
# 也能看出这次读数是在哪把尺子上量的。
_BASIS_GENERATOR_LABELS: Mapping[str, tuple[str, str]] = MappingProxyType({
    "standard_basis": ("e₁", "e₂"),
    "oblique_basis": ("b₁", "b₂"),
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
    # 4.1.3 的子空间要装下它所有的采样向量：平面盖过三支输入、三支输出的落点，
    # 否则箭头会戳出平面之外。零空间是 1 维的，任何画在轴上的线段都会被同方向的
    # 采样向量完全盖住，所以只在所有竖直向量之外各画一小段虚线，表示这条轴继续延伸；
    # 主角是那支垂直穿出平面的代表向量。
    # Keep the z=0 plane visibly present without washing out the three output
    # vectors that lie on it, especially in a narrow case pane.
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


# 场景标签不是数学证据本身，必须作为舞台专属别名注册：否则它们会绕开案例
# 可见性掩码，留在不属于自己的另一个窗格。标签里 ``x_1``、``Ax_2`` 这类
# ``letter_digits`` 写法在数据层保持可读 ASCII，由 ``math_labels.display_text``
# 在渲染时自动换成 Unicode 下标字形（``x₁``、``Ax₂``）。
_COL_NULL_STAGE_LABELS: Mapping[str, tuple[tuple[str, str, tuple[float, float, float], str], ...]] = MappingProxyType({
    "stage.ch04.subspace.col-null.column_space": (
        ("col_space", "Col(A)", (-2.35, -2.35, 0.12), "column_space"),
        # Vector labels belong beside the arrow shaft.  The tip remains the
        # endpoint marker, so putting a vector name there conflates two roles.
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
    if topic=="ch04.linear-map.compare":
        lanes={"rotation":(-8,4),"stretch":(0,4),"projection":(8,4),"translation":(-8,-4),"square_map":(0,-4),"constant_shift":(8,-4)}
        offset=lanes.get(role,(0,0))
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
            # The region protocol accepts two directions; render every member
            # separately so a redundant third generator is never discarded.
            # A basis is a pair of rulers, so each direction gets its own color
            # instead of one color for the whole set.
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
    """Return topic-local algebra labels for 3D vectors."""

    if topic_id == _COL_NULL_COLORED_TOPIC:
        rendering: dict[str, object] = {}
        symbol = _COL_NULL_VECTOR_SYMBOLS.get(role)
        if symbol is not None:
            rendering["algebra_symbol"] = symbol
        return rendering
    if topic_id == _DEPENDENCE_COLORED_TOPIC:
        rendering: dict[str, object] = {}
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
    # 箭头尖上的标记写这支向量自己的名字（e₁、x、2u……）；计划没说名字的向量就
    # 不画标记——统一写 "result" 只会让每个窗格都多出一个看不出指谁的词。
    return [{"op":"point.upsert","alias":origin,"coordinates":[0.0,0.0],"name":"O"},
            {"op":"point.upsert","alias":end,"coordinates":_vector(endpoint,2),"name":label},
            {"op":"linear.upsert","alias":alias,"start":origin,"end":end,"kind":"vector","role":"result",**_color_kwargs(color)}]


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
    grid={**readout,"op":"geometry.basis_grid","alias":f"{alias}__grid",**_color_kwargs(basis_colors[0] if basis_colors else None)}
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
        if relation.kind == "coordinate_equivalence":
            # A readout measures with one specific basis, so its grid and component
            # arrows borrow that basis's own colors.
            return _coordinate_operations(alias,p["basis_matrix"],p["coordinates"],p["expected_vector"],context,
                                          _basis_generator_colors(topic_id, source.role),
                                          _basis_generator_labels(topic_id, source.role))
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
            return _vector_relation(alias,target.value,label=target.label)
        if relation.kind == "not_linear":
            if source.kind == "constraint": return [{"op":"curve.create","alias":alias,"kind":"explicit","expression":"y=x^2"}]
            return _vector_relation(alias,p["origin_image"])
        if relation.kind == "basis_of" or (relation.kind in {"dimension_of","linear_dependence","contains"} and source.kind in {"basis","subspace"}):
            return _entity_operations(source,alias,"2d",context,topic_id)[0]
        # A target redrawn with a relation-specific alias is a geometric
        # witness of the typed relation, never a text-only bookkeeping edge.
        return _entity_operations(target,alias,"2d",context,topic_id)[0]

    if topic_id == "ch04.subspace.col-null" and relation.kind == "maps_to":
        # 4.1.3 的 maps_to 画「输入到输出的落差」：源对象已经被压到目标位置，
        # 所以关系只补一条虚线连接（颜色跟随源对象），不再把目标重画一遍——
        # 否则同一张图里会出现两个重合的平面/向量。
        start = _vector(source.value, 3)
        end = _vector(target.value, 3)
        if all(abs(value) <= TOL for value in end):
            # 目标就是原点时连线完全落在源向量自己身上（零空间把输入压成一点），
            # 画出来等于没画：只把「像」画成原点上的那个点。
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
        vectors=[_scale(vector,coefficient) for vector,coefficient in zip(_matrix(source.value),_vector(p["coefficients"]))]
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
        # 组合的落点写目标实体自己的名字（「0」），不写 "zero combination"——窗格标记
        # 是给学生看的数学写法，不是编译器的内部术语。
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
        # A 只作为关系参数存在：矩阵不是一个几何对象，画成平面会和列空间重合。
        # 每支采样向量既画在实体里、又写在关系参数里；两边必须一致，改动任何一边
        # 都会让这里重算失败。
        # 三支轴外采样输入都从同一原点出发，输出全部落在那张平面上、并把平面
        # 铺开三个方向；零空间的代表竖直采样被压到原点。
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
        independent=_matrix(value("independent_set"))
        dependent=_matrix(value("dependent_set"))
        independent_coefficients=_vector(parameters["independent_combination"]["coefficients"])
        dependent_coefficients=_vector(parameters["dependent_combination"]["coefficients"])
        independent_combination=_combination(independent, independent_coefficients)
        dependent_combination=_combination(dependent, dependent_coefficients)
        numbers.update(
            independent_rank=_rank(independent),
            dependent_rank=_rank(dependent),
            independent_combination=independent_combination,
            dependent_combination=dependent_combination,
        )
        checks["independent_only_zero_solution"] = _rank(independent) == 3
        checks["independent_span_r3"] = (
            _rank(independent) == 3
            and _close(independent_combination, value("independent_sample"))
        )
        checks["dependent_nonzero_combination_zero"] = (
            _close(dependent_combination, [0, 0, 0])
            and any(abs(value) > TOL for value in dependent_coefficients)
        )
        checks["dependent_coplanar"] = _rank(dependent) == 2
    elif topic_id == "ch04.basis.definition":
        # 定义 4.10 要两条：线性无关、生成整个空间。两组基都按列给出（基是向量组），
        # 秩 = 2 说明无冗余，与标准基张成同一个空间说明能生成整个 R²。读数部分同时
        # 核对关系参数里的基矩阵与实体值一致——任何一边被改，这里重算就会失败。
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
            entity_ops,entity_aliases=_entity_operations(entity,_entity_alias(entity.role),spec.scene_kind,context,topic_id)
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
            if topic_id in {_COL_NULL_COLORED_TOPIC, _DEPENDENCE_COLORED_TOPIC}:
                # 4.1.3 不再显示脚手架方格：列空间已由那张平面加三支采样向量铺满，
                # 再叠一个与列空间重合的单位方格会被误读成第二个集合。这里把它的别名
                # 登记为「受舞台管理」的别名、却不写进任何舞台的可见集合，于是每个案例
                # 窗格都会把它遮掉；4.2 的对照图同样不需要这块与相关平面重合的脚手架。
                # 两个主题仍保有一个协议级几何图元（见本分支上方的硬性要求）。
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
