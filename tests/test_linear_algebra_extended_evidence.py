from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from linear_algebra.registry import bundled_teaching_store, catalog_registry
from linear_algebra.visualizations.evidence import validate_extended_evidence
from services.scene_commands import CommandPlan


def _bundle(topic_id: str):
    return catalog_registry().resolve_bundle(topic_id, artifact_store=bundled_teaching_store())


def test_published_extended_topics_have_closed_evidence_links() -> None:
    registry = catalog_registry()
    for topic in registry.topics:
        if topic.chapter_number < 4:
            continue
        assert validate_extended_evidence(_bundle(topic.id)) == ()


def test_declared_quadratic_capability_requires_actual_level_set_op() -> None:
    bundle = _bundle("ch08.principal-axis")
    operations = tuple(
        operation for operation in bundle.compiled.plan.operations
        if operation.get("op") != "geometry.quadratic_level_set"
    )
    compiled = replace(bundle.compiled, plan=CommandPlan(
        scene=bundle.compiled.plan.scene,
        operations=operations,
        summary=bundle.compiled.plan.summary,
    ))
    issues = validate_extended_evidence(SimpleNamespace(
        topic=bundle.topic, artifact=bundle.artifact, compiled=compiled,
    ))
    assert any(issue.code == "missing_actual_operation" and issue.topic_id == "ch08.principal-axis" for issue in issues)


def test_formula_variable_requires_visual_or_explanation_binding() -> None:
    bundle = _bundle("ch08.principal-axis")
    claim = replace(bundle.artifact.claims[0], formula_symbols=("lambda_unbound",))
    artifact = replace(bundle.artifact, claims=(claim, *bundle.artifact.claims[1:]))
    issues = validate_extended_evidence(SimpleNamespace(
        topic=bundle.topic, artifact=artifact, compiled=bundle.compiled,
    ))
    assert any(issue.code == "unbound_formula_variable" for issue in issues)
