"""Compatibility behavior for legacy explanation resources."""

from __future__ import annotations

import pytest

from linear_algebra.explanations import explanation_for
from linear_algebra.registry import catalog_registry
from linear_algebra.teaching.legacy import adapt_legacy_explanation, publish_legacy_artifact


def test_legacy_explanation_can_be_read_as_pending_artifact() -> None:
    topic = catalog_registry().get_topic("ch01.ops.addition")
    artifact = adapt_legacy_explanation(topic, explanation_for(topic.id))

    assert artifact.migration_state == "migration_pending"
    assert artifact.visual_semantics is None
    assert catalog_registry().get_legacy_explanation(topic.id) == artifact


def test_legacy_artifact_cannot_be_published() -> None:
    topic = catalog_registry().get_topic("ch01.ops.addition")
    artifact = adapt_legacy_explanation(topic, explanation_for(topic.id))

    with pytest.raises(ValueError, match="visual_semantics"):
        publish_legacy_artifact(artifact)
