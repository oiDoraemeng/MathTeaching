"""Write reproducible automated evidence for the linear-algebra teaching change."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Iterable, Sequence

from linear_algebra.registry import catalog_registry
from linear_algebra.teaching.store import TeachingArtifactStore
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class VerificationResult:
    name: str
    command: tuple[str, ...]
    exit_code: int
    output: str


class VerificationFailed(RuntimeError):
    def __init__(self, name: str, exit_code: int, output: str) -> None:
        self.name = name
        self.exit_code = exit_code
        self.output = output
        super().__init__(f"{name} failed with exit code {exit_code}")


def resolve_pnpm() -> str:
    return shutil.which("pnpm") or "pnpm"


CHECKS: tuple[VerificationCheck, ...] = (
    VerificationCheck("python-validation", (sys.executable, "-m", "linear_algebra.validation")),
    VerificationCheck("python-tests", (sys.executable, "-m", "pytest", "-q")),
    VerificationCheck("web-tests", (resolve_pnpm(), "--dir", "ui/agent_web", "test", "--", "--run")),
    VerificationCheck("web-build", (resolve_pnpm(), "--dir", "ui/agent_web", "build")),
)


def _default_runner(check: VerificationCheck) -> VerificationResult:
    completed = subprocess.run(
        list(check.command),
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    return VerificationResult(check.name, check.command, int(completed.returncode), output)


def _coerce_result(check: VerificationCheck, value: object) -> VerificationResult:
    if isinstance(value, VerificationResult):
        return value
    exit_code = getattr(value, "exit_code", getattr(value, "returncode", None))
    if not isinstance(exit_code, int):
        raise TypeError("command runner result must expose integer exit_code or returncode")
    output = getattr(value, "output", None)
    if output is None:
        output = (getattr(value, "stdout", "") or "") + (getattr(value, "stderr", "") or "")
    return VerificationResult(check.name, check.command, exit_code, str(output))


def compile_all_topic_digests(
    *,
    artifact_root: str | Path | None = None,
) -> tuple[dict[str, object], ...]:
    """Compile every published artifact into a stable digest projection."""

    root_value = artifact_root or os.environ.get("MATH3D_TEACHING_ARTIFACT_ROOT", "")
    root = Path(root_value) if str(root_value).strip() else Path(__file__).parents[1] / "linear_algebra" / "teaching" / "data"
    store = TeachingArtifactStore(root)
    registry = catalog_registry()
    compiler = VisualSemanticsCompiler()
    rows: list[dict[str, object]] = []
    for topic in registry.topics:
        stored = store.published(topic.id)
        if stored is None:
            continue
        artifact = stored.artifact
        compiled = compiler.compile(artifact, context=RenderContext.default(topic.id))
        rows.append(
            {
                "topic_id": topic.id,
                "revision": artifact.revision,
                "source_hash": artifact.source.source_hash,
                "artifact_digest": artifact.generated.artifact_digest,
                "compiler_version": compiled.compiler_version,
                "render_profile": compiled.render_profile,
                "plan_digest": compiled.plan_digest,
                "stage_count": len(compiled.storyboard),
                "claim_count": len(artifact.claims),
            }
        )
    return tuple(sorted(rows, key=lambda row: str(row["topic_id"])))


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def run_verification(
    command_runner: Callable[[VerificationCheck], object] = _default_runner,
    output_dir: str | Path = Path("openspec/changes/enrich-linear-algebra-teaching-depth/verification"),
    *,
    checks: Iterable[VerificationCheck] = CHECKS,
    digest_loader: Callable[[], tuple[dict[str, object], ...]] | None = None,
) -> tuple[VerificationResult, ...]:
    """Run all checks and write evidence only after every check succeeds."""

    results: list[VerificationResult] = []
    for check in checks:
        result = _coerce_result(check, command_runner(check))
        results.append(result)
        if result.exit_code != 0:
            raise VerificationFailed(result.name, result.exit_code, result.output)
    digests = tuple(
        sorted(
            (digest_loader() if digest_loader is not None else compile_all_topic_digests()),
            key=lambda row: str(row.get("topic_id", "")),
        )
    )
    if len(digests) != 54:
        raise VerificationFailed("topic-digests", 1, f"expected 54 published topics, got {len(digests)}")
    destination = Path(output_dir)
    _write_atomic(destination / "topic-digests.json", json.dumps(list(digests), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    lines = ["# Automated Validation", "", f"Topic digests: {len(digests)}", ""]
    for result in results:
        lines.extend(
            [
                f"## {result.name}",
                f"- command: `{_display_command(result.command)}`",
                f"- exit code: {result.exit_code}",
                "- output:",
                "```text",
                result.output.rstrip(),
                "```",
                "",
            ]
        )
    _write_atomic(destination / "automated-validation.md", "\n".join(lines).rstrip() + "\n")
    return tuple(results)


_FOCUS_TOPICS = (
    "ch01.projection.definition",
    "ch01.ops.cross-product",
    "ch02.matrix.transformed-grid",
    "ch02.matrix.composition",
    "ch02.subspace.null",
    "ch03.det.multiplicativity",
    "ch03.inverse.undo",
)


def write_walkthrough_index(digest_path: str | Path, output_path: str | Path) -> None:
    payload = json.loads(Path(digest_path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("topic-digests.json must contain an array")
    rows = {str(item.get("topic_id")): item for item in payload if isinstance(item, dict)}
    missing = [topic_id for topic_id in _FOCUS_TOPICS if topic_id not in rows]
    if missing:
        raise ValueError("missing focus topic digests: " + ", ".join(missing))
    lines = [
        "# Manual Walkthrough",
        "",
        "| topic_id | revision | source_hash | artifact_digest | compiler_version | plan_digest | explanation | visual | storyboard | result |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for topic_id in sorted(_FOCUS_TOPICS):
        row = rows[topic_id]
        lines.append(
            "| {topic_id} | {revision} | {source_hash} | {artifact_digest} | {compiler_version} | {plan_digest} | not-checked | not-checked | not-checked | not-checked |".format(
                topic_id=topic_id,
                revision=row.get("revision", ""),
                source_hash=row.get("source_hash", ""),
                artifact_digest=row.get("artifact_digest", ""),
                compiler_version=row.get("compiler_version", ""),
                plan_digest=row.get("plan_digest", ""),
            )
        )
    lines.extend(["", "## Rollback", "", "not-checked", ""])
    _write_atomic(Path(output_path), "\n".join(lines))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    automated = subparsers.add_parser("automated")
    automated.add_argument("--output-dir", type=Path, required=True)
    walkthrough = subparsers.add_parser("walkthrough-index")
    walkthrough.add_argument("--digests", type=Path, required=True)
    walkthrough.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "automated":
        run_verification(output_dir=args.output_dir)
    else:
        write_walkthrough_index(args.digests, args.output)
    return 0


def _display_command(command: Sequence[str]) -> str:
    return " ".join(str(part) for part in command)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
