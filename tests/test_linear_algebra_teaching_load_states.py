import pytest

from linear_algebra.teaching.load_states import LoadPhase, LoadTransaction


def test_commit_requires_staged_payload():
    transaction = LoadTransaction("ch04.subspace.col-null")
    transaction.advance(LoadPhase.RESOLVING)
    with pytest.raises(ValueError, match="staged"):
        transaction.advance(LoadPhase.COMMITTED)


def test_rejection_retains_previous_revision_metadata():
    transaction = LoadTransaction("ch08.principal-axis", previous_revision=3)
    transaction.advance(LoadPhase.RESOLVING)
    transaction.advance(LoadPhase.SOURCE_CHECKED)
    diagnostic = transaction.reject("source_stale", LoadPhase.SOURCE_CHECKED, "source_hash")
    assert diagnostic.code == "source_stale"
    assert transaction.previous_revision == 3


def test_transitions_are_explicit_and_diagnostic_is_frozen():
    transaction = LoadTransaction("ch04.topic")
    transaction.advance(LoadPhase.RESOLVING)
    transaction.advance(LoadPhase.SOURCE_CHECKED)
    transaction.advance(LoadPhase.ARTIFACT_CHECKED)
    assert transaction.phase is LoadPhase.ARTIFACT_CHECKED
    diagnostic = transaction.reject("numeric_invalid", LoadPhase.ARTIFACT_CHECKED, "value", "not finite")
    assert transaction.phase is LoadPhase.REJECTED
    assert transaction.diagnostic == diagnostic
    with pytest.raises(ValueError, match="rejected"):
        transaction.advance(LoadPhase.RESOLVING)


def test_commit_requires_staged_and_preserves_snapshot():
    transaction = LoadTransaction("ch04.topic")
    for phase in (
        LoadPhase.RESOLVING, LoadPhase.SOURCE_CHECKED, LoadPhase.ARTIFACT_CHECKED,
        LoadPhase.CONTRACT_CHECKED, LoadPhase.COMPILED, LoadPhase.PLAN_VALIDATED,
        LoadPhase.STAGED, LoadPhase.COMMITTED,
    ):
        transaction.advance(phase)
    snapshot = transaction.snapshot()
    assert snapshot.phase is LoadPhase.COMMITTED
    assert snapshot.topic_id == "ch04.topic"
    with pytest.raises(ValueError, match="committed"):
        transaction.reject("plan_invalid", LoadPhase.COMMITTED, "plan")


def test_reject_is_frozen_and_requires_current_phase():
    transaction = LoadTransaction("ch04.topic")
    diagnostic = transaction.reject("numeric_invalid", LoadPhase.IDLE, "value")
    with pytest.raises(ValueError, match="rejected"):
        transaction.reject("plan_invalid", LoadPhase.REJECTED, "plan")
    assert transaction.diagnostic is diagnostic
    other = LoadTransaction("ch04.other")
    with pytest.raises(ValueError, match="match current"):
        other.reject("numeric_invalid", LoadPhase.SOURCE_CHECKED, "value")


def test_allowed_transition_map_is_immutable():
    with pytest.raises(TypeError):
        LoadTransaction._ALLOWED[LoadPhase.IDLE] = frozenset()
