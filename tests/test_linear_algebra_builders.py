"""Tests for linear algebra visualization builders."""

import math

import pytest

from linear_algebra.catalog.model import LessonEntry, SourceAnchor
from linear_algebra.visualizations.builders import get_builder_for
from linear_algebra.visualizations.builders.math_utils import (
    angle_between,
    cross_product,
    dot_product,
    project_vector,
)
from linear_algebra.visualizations.builders.primitives import (
    make_label,
    make_polygon,
    make_vector_2d,
    make_view_fit,
)


def test_get_builder_for_returns_none_for_unknown_id():
    """Test registry returns None for unknown visualization ID"""
    builder = get_builder_for("unknown.id")
    assert builder is None


def test_dot_product():
    """Test dot product calculation"""
    v1 = [3.0, 4.0]
    v2 = [1.0, 2.0]
    result = dot_product(v1, v2)
    assert result == 11.0


def test_project_vector():
    """Test vector projection"""
    v = [3.0, 1.0]
    u = [2.0, 0.0]
    proj = project_vector(v, u)
    assert proj == [3.0, 0.0]


def test_angle_between():
    """Test angle calculation between vectors"""
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    angle = angle_between(v1, v2)
    assert abs(angle - math.pi / 2) < 0.001


def test_cross_product():
    """Test 3D cross product"""
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    result = cross_product(v1, v2)
    assert result == [0.0, 0.0, 1.0]


def test_make_vector_2d():
    """Test 2D vector primitive creation"""
    ops = make_vector_2d([0, 0], [2, 1], "v", role="primary", style="solid")

    assert len(ops) == 3
    assert ops[0]["op"] == "point.upsert"
    assert ops[0]["coordinates"] == [0, 0]
    assert ops[1]["op"] == "point.upsert"
    assert ops[1]["coordinates"] == [2, 1]
    assert ops[2]["op"] == "linear.upsert"
    assert ops[2]["kind"] == "vector"
    assert ops[2]["role"] == "primary"
    assert ops[2]["style"] == "solid"


def test_make_vector_role_aliases_use_scene_protocol_roles():
    assert make_vector_2d([0, 0], [1, 1], "secondary", role="secondary")[2]["role"] == "construction"
    assert make_vector_2d([0, 0], [1, 1], "aux", role="auxiliary")[2]["role"] == "construction"


def test_make_label():
    """Test label primitive creation"""
    op = make_label("a", [1.0, 0.5], offset=[-0.2, -0.2])

    assert op["op"] == "annotation.formula"
    assert op["text"] == "a"
    assert op["position"] == [1.0, 0.5]
    assert op["alias"] == "label_a"


def test_make_polygon():
    """Test polygon primitive creation"""
    vertices = [[0, 0], [2, 1], [3, 3], [1, 2]]
    op = make_polygon(vertices, color="#5b8def", opacity=0.15, outline=True)

    assert op["op"] == "geometry.polygon"
    assert op["vertices"] == vertices
    assert op["color"] == "#5b8def"
    assert op["opacity"] == 0.15
    assert op["outline"] is True


def test_make_view_fit():
    """Test view fit primitive creation"""
    op = make_view_fit(padding=1.15)

    assert op["op"] == "view.fit"
    assert op["padding"] == 1.15


def test_recipe_for_entry_raises_for_missing_builder():
    """Test that recipe_for_entry raises when no builder found"""
    from linear_algebra.visualizations.common import recipe_for_entry

    entry = LessonEntry(
        id="test.topic",
        chapter_number=1,
        section_id="test.s1",
        title="Test Topic",
        source_path=("Chapter", "Section", "Topic"),
        source_anchor=SourceAnchor(("Chapter",), 2),
        explanation_id="explain.test.topic",
        visualization_id="draw.test.topic",
        required_capabilities=("vector_2d",),
    )

    with pytest.raises(ValueError, match="No builder found"):
        recipe_for_entry(entry)
