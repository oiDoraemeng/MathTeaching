from types import SimpleNamespace

from linear_algebra.registry import bundled_teaching_store, catalog_registry
from ui.teaching_case_panes import StoryboardVisibilityController


def test_representative_topic_storyboards_are_selectable_without_host_calls() -> None:
    for topic_id in (
        "ch04.subspace.col-null",
        "ch05.consistency.geometry",
        "ch06.similarity-transform",
        "ch07.diagonalization",
        "ch08.principal-axis",
    ):
        bundle = catalog_registry().resolve_bundle(topic_id, artifact_store=bundled_teaching_store())
        controller = StoryboardVisibilityController(bundle.compiled)
        assert controller.select(bundle.compiled.storyboard[0].id).stage_id == bundle.compiled.storyboard[0].id


def test_unknown_stage_does_not_mutate_runtime_visibility() -> None:
    bundle = catalog_registry().resolve_bundle("ch08.principal-axis", artifact_store=bundled_teaching_store())
    controller = StoryboardVisibilityController(bundle.compiled)
    runtime = SimpleNamespace(
        geometry_controller=SimpleNamespace(set_agent_alias_visible=lambda *_: (_ for _ in ()).throw(AssertionError())),
        geometry3d_controller=None,
    )
    try:
        controller.apply(runtime, "missing-stage")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown stage must be rejected")
