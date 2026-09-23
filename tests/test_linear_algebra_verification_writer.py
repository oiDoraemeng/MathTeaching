import json
from pathlib import Path

import pytest

from scripts.write_linear_algebra_verification import (
    VerificationCheck,
    VerificationFailed,
    VerificationResult,
    run_verification,
    write_walkthrough_index,
)


def _checks() -> tuple[VerificationCheck, ...]:
    return (VerificationCheck("python-validation", ("python", "-m", "linear_algebra.validation")),)


def test_writer_stops_on_failed_check_and_does_not_claim_success(tmp_path: Path) -> None:
    def runner(check: VerificationCheck) -> VerificationResult:
        return VerificationResult(check.name, check.command, 1, "invalid topic ch03.inverse")

    with pytest.raises(VerificationFailed, match="python-validation"):
        run_verification(runner, tmp_path, checks=_checks(), digest_loader=lambda: ())
    assert not (tmp_path / "automated-validation.md").exists()
    assert not (tmp_path / "topic-digests.json").exists()


def test_writer_records_success_output_and_sorted_digests(tmp_path: Path) -> None:
    def runner(check: VerificationCheck) -> VerificationResult:
        return VerificationResult(check.name, check.command, 0, "28 topics validated")

    digests = tuple(
        {"topic_id": topic_id, "revision": 1, "source_hash": "sha256:source", "artifact_digest": "sha256:artifact", "compiler_version": "visual-compiler-v1", "plan_digest": f"sha256:{topic_id}"}
        for topic_id in reversed([f"ch01.topic-{index:02d}" for index in range(28)])
    )
    run_verification(runner, tmp_path, checks=_checks(), digest_loader=lambda: digests)
    report = (tmp_path / "automated-validation.md").read_text(encoding="utf-8")
    assert "28 topics validated" in report
    assert "exit code: 0" in report
    saved = json.loads((tmp_path / "topic-digests.json").read_text(encoding="utf-8"))
    assert [item["topic_id"] for item in saved] == sorted(item["topic_id"] for item in saved)


def test_walkthrough_index_requires_all_focus_digests(tmp_path: Path) -> None:
    digest_path = tmp_path / "topic-digests.json"
    digest_path.write_text(json.dumps([], ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="missing focus topic digests"):
        write_walkthrough_index(digest_path, tmp_path / "manual-walkthrough.md")


def test_writer_redacts_provider_tokens_from_persisted_output(tmp_path: Path) -> None:
    def runner(check: VerificationCheck) -> VerificationResult:
        return VerificationResult(check.name, check.command, 0, "api_key=secret-value sk-1234567890123456")

    digests = tuple(
        {"topic_id": f"ch01.topic-{index:02d}", "revision": 1, "source_hash": "s", "artifact_digest": "a", "compiler_version": "c", "plan_digest": "p"}
        for index in range(28)
    )
    run_verification(runner, tmp_path, checks=_checks(), digest_loader=lambda: digests)
    report = (tmp_path / "automated-validation.md").read_text(encoding="utf-8")
    assert "secret-value" not in report
    assert "[REDACTED]" in report
