from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.validation import validate_claim_bindings
from tests.teaching_fixtures import composition_artifact_payload, projection_artifact_payload


def test_composition_claim_binds_formula_symbols_and_two_stages() -> None:
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())

    assert validate_claim_bindings(artifact) == ()


def test_projection_claim_without_residual_evidence_fails() -> None:
    artifact = TeachingArtifact.from_dict(projection_artifact_payload(with_residual=False))

    issues = validate_claim_bindings(artifact)

    assert any(issue.code == "claim_missing_evidence" for issue in issues)
    assert any(issue.path == "$.claims[0].entity_refs" for issue in issues)


def test_formula_symbols_are_declarations_not_tex_tokens() -> None:
    payload = composition_artifact_payload()
    payload["claims"][0]["formula"] = r"\\operatorname{det}(A) = ad-bc"  # type: ignore[index]
    payload["claims"][0]["formula_symbols"] = ["A", "a", "b", "c", "d"]  # type: ignore[index]
    artifact = TeachingArtifact.from_dict(payload)

    issues = validate_claim_bindings(artifact)

    assert [issue.code for issue in issues] == [
        "unbound_formula_symbol",
        "unbound_formula_symbol",
        "unbound_formula_symbol",
        "unbound_formula_symbol",
    ]
    assert all("formula_symbols" in issue.path for issue in issues)


def test_claim_evidence_requires_reverse_links_and_closed_ids() -> None:
    payload = composition_artifact_payload()
    payload["claims"][0]["relation_refs"] = ["missing-relation"]  # type: ignore[index]
    payload["visual_semantics"]["entities"][0]["claim_refs"] = []  # type: ignore[index]
    artifact = TeachingArtifact.from_dict(payload)

    issues = validate_claim_bindings(artifact)

    assert ("$.claims[0].relation_refs[0]", "dangling_reference") in {
        (issue.path, issue.code) for issue in issues
    }
    assert ("$.claims[0].entity_refs[0]", "claim_missing_evidence") in {
        (issue.path, issue.code) for issue in issues
    }
