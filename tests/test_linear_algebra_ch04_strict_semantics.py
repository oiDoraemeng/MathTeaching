"""Strict chapter 4 semantic contract and family-boundary checks."""
import pytest

from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler, VisualCompileError
from linear_algebra.visualizations.contracts import contract_for
from linear_algebra.chapter_04_semantics import semantic_for

TOPICS = tuple(sorted(k for k in load_reviewed_artifacts() if k.startswith("ch04.")))

def test_all_ch04_claims_bind_every_role_and_relation_to_distinct_evidence():
    compiler = VisualSemanticsCompiler()
    for topic in TOPICS:
        artifact = TeachingArtifact.from_dict(load_reviewed_artifacts()[topic])
        compiled = compiler.compile(artifact, contract_for(topic), RenderContext.default(topic))
        claim = artifact.claims[0]
        aliases = [compiled.aliases_for(ref) for ref in (*claim.entity_refs, *claim.relation_refs)]
        assert all(aliases)
        assert len({values[0] for values in aliases}) == len(aliases)

def test_family_compile_is_mandatory(monkeypatch):
    from linear_algebra.visualizations.families import SceneFamilyCompiler
    def fail(self, *args, **kwargs): raise RuntimeError("family invoked")
    monkeypatch.setattr(SceneFamilyCompiler, "compile", fail)
    artifact = TeachingArtifact.from_dict(load_reviewed_artifacts()[TOPICS[0]])
    with pytest.raises(RuntimeError, match="family invoked"):
        VisualSemanticsCompiler().compile(artifact, contract_for(TOPICS[0]), RenderContext.default(TOPICS[0]))

@pytest.mark.parametrize("topic", TOPICS)
def test_topic_contract_requires_all_declared_roles_and_invariants(topic):
    artifact = TeachingArtifact.from_dict(load_reviewed_artifacts()[topic])
    semantic = semantic_for(topic)
    contract = contract_for(topic)
    assert set(contract.required_entity_roles) >= set(semantic.roles)
    assert set(contract.required_invariants) >= set(semantic.invariants)

