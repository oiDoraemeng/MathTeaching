import math

import pytest

from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.limits import RenderLimits, limits_for, validate_budget
from linear_algebra.visualizations.compiler import VisualCompileError, VisualSemanticsCompiler
from linear_algebra.teaching.model import VisualEntity, VisualSemantics


def test_lecture_profile_has_fixed_resource_budget():
    limits = limits_for("lecture-v1")
    assert limits == RenderLimits("lecture-v1", 48, 32, 6, 128 * 128, 64 * 64 * 64, 1e-9, 1e-7)


def test_lecture_profile_rejects_excessive_3d_samples():
    errors = validate_budget("lecture-v1", scene="3d", entity_count=2, stage_count=1, sample_count=64 * 64 * 64 + 1, bounds=(-3, 3, -3, 3))
    assert any("samples" in error for error in errors)


@pytest.mark.parametrize("bounds", [(3, -3, -3, 3), (0, 1, 2, 1), (math.nan, 1, 0, 1)])
def test_budget_rejects_invalid_bounds(bounds):
    assert validate_budget("lecture-v1", scene="2d", entity_count=1, stage_count=1, sample_count=1, bounds=bounds)


def test_context_resolves_immutable_profile_limits():
    context = RenderContext.default("ch04.topic")
    assert context.limits == limits_for("lecture-v1")
    with pytest.raises(AttributeError):
        context.limits = limits_for("lecture-v1")


def test_compiler_rejects_scene_bounds_dimension_before_plan_output():
    semantics = VisualSemantics(scene_kind="2d", entities=(), relations=(), stages=())
    context = RenderContext("ch01.ops.addition", bounds=(-3, 3, -3, 3, -3, 3), render_profile="lecture-v1")
    with pytest.raises(VisualCompileError, match="bounds"):
        VisualSemanticsCompiler().compile(semantics, topic_id="ch01.ops.addition", context=context)
