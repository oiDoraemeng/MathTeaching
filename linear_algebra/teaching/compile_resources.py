"""Compile published teaching semantics into deterministic runtime resources."""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
from typing import Mapping

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.registry import catalog_registry
from linear_algebra.teaching.store import TeachingArtifactStore, artifact_digest
from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import contract_for
from linear_algebra.visualizations.snapshots import CompiledSnapshotStore, snapshot_from
from linear_algebra.visualizations.snapshots import contract_digest_for


@dataclass(frozen=True)
class CompiledResource:
    topic_id: str
    revision: int
    artifact_digest: str
    source_hash: str
    compiler_version: str
    render_profile: str
    plan_digest: str
    plan: Mapping[str, object]
    stages: tuple[Mapping[str, object], ...]
    read_guide: tuple[str, ...]
    claim_count: int
    contract_digest: str = ""
    scene_family: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "topic_id": self.topic_id,
            "revision": self.revision,
            "artifact_digest": self.artifact_digest,
            "source_hash": self.source_hash,
            "compiler_version": self.compiler_version,
            "render_profile": self.render_profile,
            "plan_digest": self.plan_digest,
            "plan": dict(self.plan),
            "stages": [dict(stage) for stage in self.stages],
            "read_guide": list(self.read_guide),
            "claim_count": self.claim_count,
            "contract_digest": self.contract_digest,
            "scene_family": self.scene_family,
        }


class CompiledResourceStore:
    """Stable filesystem store for semantic compilation records."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def path_for(self, topic_id: str) -> Path:
        if not topic_id.startswith("ch") or "/" in topic_id or "\\" in topic_id:
            raise ValueError("unsafe topic id")
        return self.root / f"{topic_id}.json"

    def save(self, resource: CompiledResource) -> Path:
        path = self.path_for(resource.topic_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(resource.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(path)
        return path

    def get(self, topic_id: str) -> CompiledResource:
        path = self.path_for(topic_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("compiled resource must be an object")
        stages = payload.get("stages", [])
        if not isinstance(stages, list) or not all(isinstance(stage, dict) for stage in stages):
            raise ValueError("compiled resource stages must be objects")
        plan = payload.get("plan", {})
        if not isinstance(plan, dict):
            raise ValueError("compiled resource plan must be an object")
        read_guide = payload.get("read_guide", [])
        if not isinstance(read_guide, list) or not all(isinstance(value, str) for value in read_guide):
            raise ValueError("compiled resource read_guide must be strings")
        return CompiledResource(
            topic_id=str(payload["topic_id"]),
            revision=int(payload["revision"]),
            artifact_digest=str(payload["artifact_digest"]),
            source_hash=str(payload["source_hash"]),
            compiler_version=str(payload["compiler_version"]),
            render_profile=str(payload["render_profile"]),
            plan_digest=str(payload["plan_digest"]),
            plan=plan,
            stages=tuple(stages),
            read_guide=tuple(read_guide),
            claim_count=int(payload.get("claim_count", 0)),
            contract_digest=str(payload.get("contract_digest", "")),
            scene_family=str(payload.get("scene_family", "")),
        )


def compiled_resource_store(root: str | Path | None = None) -> CompiledResourceStore:
    path = Path(root) if root is not None else Path(__file__).with_name("data") / "compiled"
    return CompiledResourceStore(path)


def compile_published_topic(
    topic_id: str,
    *,
    artifact_store: TeachingArtifactStore | None = None,
) -> CompiledResource:
    store = artifact_store or TeachingArtifactStore(Path(__file__).with_name("data"))
    stored = store.published(topic_id)
    if stored is None:
        raise FileNotFoundError(f"missing published artifact {topic_id}")
    artifact = stored.artifact
    contract = contract_for(topic_id)
    compiled = VisualSemanticsCompiler().compile(
        artifact,
        contract,
        RenderContext.default(topic_id),
    )
    stages = tuple(
        {
            "id": stage.id,
            "title": stage.title,
            "caption": stage.caption,
            "layout": stage.layout,
            "visible_refs": list(stage.visible_refs),
            "visible_aliases": list(stage.visible_aliases),
            "anchor": list(stage.anchor),
        }
        for stage in compiled.storyboard
    )
    return CompiledResource(
        topic_id=topic_id,
        revision=artifact.revision,
        artifact_digest=artifact_digest(artifact),
        source_hash=artifact.source.source_hash,
        compiler_version=compiled.compiler_version,
        render_profile=compiled.render_profile,
        plan_digest=compiled.plan_digest,
        plan=compiled.plan.to_dict(),
        stages=stages,
        read_guide=artifact.explanation.read_guide,
        claim_count=len(artifact.claims),
        contract_digest=contract_digest_for(contract),
        scene_family=artifact.visual_semantics.scene_family,
    )


def compile_reviewed_topic(topic_id: str) -> CompiledResource:
    """Compile one reviewed artifact without publishing it.

    This chapter-scoped path is used while a chapter is being released; the
    normal registry/compiler path remains publication-gated for all chapters.
    """
    payload = load_reviewed_artifacts()[topic_id]
    artifact = TeachingArtifact.from_dict(payload)
    contract = contract_for(topic_id)
    compiled = VisualSemanticsCompiler().compile(
        artifact, contract, RenderContext.default(topic_id)
    )
    stages = tuple(
        {
            "id": stage.id,
            "title": stage.title,
            "caption": stage.caption,
            "layout": stage.layout,
            "visible_refs": list(stage.visible_refs),
            "visible_aliases": list(stage.visible_aliases),
            "anchor": list(stage.anchor),
        }
        for stage in compiled.storyboard
    )
    return CompiledResource(
        topic_id=topic_id,
        revision=artifact.revision,
        artifact_digest=artifact_digest(artifact),
        source_hash=artifact.source.source_hash,
        compiler_version=compiled.compiler_version,
        render_profile=compiled.render_profile,
        plan_digest=compiled.plan_digest,
        plan=compiled.plan.to_dict(),
        stages=stages,
        read_guide=artifact.explanation.read_guide,
        claim_count=len(artifact.claims),
        contract_digest=contract_digest_for(contract),
        scene_family=artifact.visual_semantics.scene_family,
    )


def compile_chapter_04(
    *,
    output_root: str | Path | None = None,
    sync_index: bool = True,
    index_path: str | Path | None = None,
) -> tuple[CompiledResource, ...]:
    """Build all sixteen chapter-4 resources and upsert their index rows.

    Compilation of every topic completes before a resource or index is
    touched.  The index update is chapter-scoped: every existing Chapter 4 row
    is replaced by the validated resource set, while rows for all other
    chapters are preserved verbatim.
    """
    topic_ids = tuple(sorted(topic_id for topic_id in load_reviewed_artifacts() if topic_id.startswith("ch04.")))
    if len(topic_ids) != 16:
        raise ValueError(f"chapter 4 requires 16 reviewed artifacts, found {len(topic_ids)}")
    resources = tuple(compile_reviewed_topic(topic_id) for topic_id in topic_ids)
    output = compiled_resource_store(output_root)
    if sync_index:
        destination = (
            Path(index_path)
            if index_path is not None
            else (Path(output_root).parent / "index.json" if output_root is not None else Path(__file__).with_name("data") / "index.json")
        )
        # Validate the complete chapter replacement before writing resources or
        # the aggregate index.  A malformed baseline therefore leaves files
        # untouched rather than producing a partial release.
        index_payload = _merged_chapter_index_payload(resources, chapter=4, output_path=destination)
    else:
        destination = None
        index_payload = None
    for resource in resources:
        output.save(resource)
    if destination is not None and index_payload is not None:
        _atomic_write_json(destination, index_payload)
    return resources


def compile_all(*, artifact_root: str | Path | None = None, output_root: str | Path | None = None) -> tuple[CompiledResource, ...]:
    artifact_store = TeachingArtifactStore(artifact_root or Path(__file__).with_name("data"))
    output = compiled_resource_store(output_root)
    resources = tuple(compile_published_topic(topic.id, artifact_store=artifact_store) for topic in topic_entries())
    for resource in resources:
        output.save(resource)
    return resources


@dataclass(frozen=True)
class CompiledResourceReport:
    count: int
    errors: tuple[str, ...]


def validate_compiled_resources(
    artifact_store: TeachingArtifactStore | None = None,
    resource_store: CompiledResourceStore | None = None,
) -> CompiledResourceReport:
    artifact_store = artifact_store or TeachingArtifactStore(Path(__file__).with_name("data"))
    resource_store = resource_store or compiled_resource_store()
    errors: list[str] = []
    count = 0
    for topic in topic_entries():
        # Release validation is publication-scoped.  Reviewed chapter bundles
        # (notably ch04 during its release gate) are validated by their
        # chapter-scoped helper and must not make the published registry fail.
        if artifact_store.published(topic.id) is None:
            continue
        try:
            resource = resource_store.get(topic.id)
            rebuilt = compile_published_topic(topic.id, artifact_store=artifact_store)
        except (FileNotFoundError, OSError, ValueError, KeyError) as error:
            errors.append(f"{topic.id}: {error}")
            continue
        count += 1
        if resource.topic_id != topic.id:
            errors.append(f"{topic.id}: resource topic mismatch")
        for field in ("artifact_digest", "source_hash", "compiler_version", "render_profile", "plan_digest"):
            if getattr(resource, field) != getattr(rebuilt, field):
                errors.append(f"{topic.id}: {field} mismatch")
        if resource.claim_count != rebuilt.claim_count:
            errors.append(f"{topic.id}: claim_count mismatch")
        if resource.stages != rebuilt.stages:
            errors.append(f"{topic.id}: stage metadata mismatch")
    return CompiledResourceReport(count=count, errors=tuple(errors))


def _digest_rows(resources: tuple[CompiledResource, ...]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "topic_id": resource.topic_id,
            "revision": resource.revision,
            "source_hash": resource.source_hash,
            "artifact_digest": resource.artifact_digest,
            "compiler_version": resource.compiler_version,
            "render_profile": resource.render_profile,
            "plan_digest": resource.plan_digest,
            "stage_count": len(resource.stages),
            "claim_count": resource.claim_count,
        }
        for resource in sorted(resources, key=lambda item: item.topic_id)
    )


def _chapter_index_rows(
    resources: tuple[CompiledResource, ...], *, chapter: int
) -> tuple[dict[str, object], ...]:
    if isinstance(chapter, bool) or not isinstance(chapter, int) or chapter < 1:
        raise ValueError("chapter must be a positive integer")
    prefix = f"ch{chapter:02d}."
    expected_ids = {
        topic.id for topic in topic_entries() if topic.chapter_number == chapter
    }
    actual_ids = [resource.topic_id for resource in resources]
    if len(actual_ids) != len(set(actual_ids)):
        raise ValueError(f"chapter {chapter} resources contain duplicate topic IDs")
    if any(not topic_id.startswith(prefix) for topic_id in actual_ids):
        raise ValueError(f"chapter {chapter} resources contain an out-of-scope topic")
    if set(actual_ids) != expected_ids:
        missing = sorted(expected_ids - set(actual_ids))
        extra = sorted(set(actual_ids) - expected_ids)
        raise ValueError(
            f"chapter {chapter} resource coverage mismatch: missing={missing}, extra={extra}"
        )
    rows: list[dict[str, object]] = []
    for resource in resources:
        linked_strings = {
            "source_hash": resource.source_hash,
            "artifact_digest": resource.artifact_digest,
            "compiler_version": resource.compiler_version,
            "render_profile": resource.render_profile,
            "contract_digest": resource.contract_digest,
            "scene_family": resource.scene_family,
            "plan_digest": resource.plan_digest,
        }
        empty = [name for name, value in linked_strings.items() if not value.strip()]
        if empty:
            raise ValueError(
                f"{resource.topic_id}: empty index linkage fields {sorted(empty)}"
            )
        rows.append(
            {
                "topic_id": resource.topic_id,
                "chapter": chapter,
                "revision": resource.revision,
                "draft_revision": resource.revision,
                "reviewed_revision": resource.revision,
                "published_revision": resource.revision,
                **linked_strings,
                "stage_count": len(resource.stages),
                "claim_count": resource.claim_count,
            }
        )
    return tuple(sorted(rows, key=lambda item: str(item["topic_id"])))


def upsert_chapter_index(
    resources: tuple[CompiledResource, ...],
    *,
    chapter: int,
    output_path: str | Path | None = None,
) -> Path:
    """Atomically replace exactly one chapter in the aggregate teaching index."""

    destination = Path(output_path) if output_path is not None else Path(__file__).with_name("data") / "index.json"
    payload = _merged_chapter_index_payload(resources, chapter=chapter, output_path=destination)
    _atomic_write_json(destination, payload)
    return destination


def _merged_chapter_index_payload(
    resources: tuple[CompiledResource, ...], *, chapter: int, output_path: str | Path
) -> dict[str, object]:
    replacement_rows = _chapter_index_rows(resources, chapter=chapter)
    destination = Path(output_path)
    if destination.is_file():
        payload = json.loads(destination.read_text(encoding="utf-8"))
    else:
        payload = {"schema_version": 1, "topics": []}
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("index payload must be a schema-version-1 object")
    current_rows = payload.get("topics")
    if not isinstance(current_rows, list) or not all(isinstance(row, dict) for row in current_rows):
        raise ValueError("index payload must contain object topic rows")
    prefix = f"ch{chapter:02d}."
    retained_rows = [
        dict(row)
        for row in current_rows
        if not str(row.get("topic_id", "")).startswith(prefix)
    ]
    retained_ids = [str(row.get("topic_id", "")) for row in retained_rows]
    if any(not topic_id for topic_id in retained_ids) or len(retained_ids) != len(set(retained_ids)):
        raise ValueError("retained index rows must have unique non-empty topic IDs")
    replacement_ids = {str(row["topic_id"]) for row in replacement_rows}
    if replacement_ids & set(retained_ids):
        raise ValueError("chapter replacement collides with retained index rows")
    updated = dict(payload)
    updated_rows = sorted(
        [*retained_rows, *(dict(row) for row in replacement_rows)],
        key=lambda item: str(item["topic_id"]),
    )
    updated["topics"] = updated_rows
    updated["topic_count"] = len(updated_rows)
    return updated


def _atomic_write_json(destination: Path, payload: Mapping[str, object]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_teaching_index(
    *,
    artifact_store: TeachingArtifactStore | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """Write one aggregate index for all published chapter resources."""

    artifact_store = artifact_store or TeachingArtifactStore(Path(__file__).with_name("data"))
    destination = Path(output_path) if output_path is not None else Path(__file__).with_name("data") / "index.json"
    topics: list[dict[str, object]] = []
    for topic in topic_entries():
        revisions = artifact_store.list_revisions(topic.id, "published")
        if not revisions:
            continue
        stored = artifact_store.get(topic.id, revisions[-1].revision, "published")
        artifact = stored.artifact
        topics.append(
            {
                "topic_id": topic.id,
                "chapter": topic.chapter_number,
                "revision": artifact.revision,
                "draft_revision": artifact.revision,
                "reviewed_revision": artifact.revision,
                "published_revision": artifact.revision,
                "source_hash": artifact.source.source_hash,
                "artifact_digest": artifact.generated.artifact_digest,
            }
        )
    payload = {"schema_version": 1, "topic_count": len(topics), "topics": sorted(topics, key=lambda item: str(item["topic_id"]))}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(destination)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="compile every published topic")
    parser.add_argument("--verify", action="store_true", help="verify existing compiled resources")
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--write-digests", type=Path)
    args = parser.parse_args(argv)
    resources = compile_all(artifact_root=args.artifact_root, output_root=args.output_root)
    if args.verify:
        report = validate_compiled_resources(
            TeachingArtifactStore(args.artifact_root or Path(__file__).with_name("data")),
            compiled_resource_store(args.output_root),
        )
        if report.count != 54 or report.errors:
            for error in report.errors:
                print(error)
            return 1
    if args.write_digests:
        args.write_digests.parent.mkdir(parents=True, exist_ok=True)
        args.write_digests.write_text(
            json.dumps(list(_digest_rows(resources)), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps({"compiled": len(resources), "verified": bool(args.verify)}, ensure_ascii=False, sort_keys=True))
    return 0


__all__ = [
    "CompiledResource",
    "CompiledResourceReport",
    "CompiledResourceStore",
    "compile_all",
    "compile_published_topic",
    "compile_reviewed_topic",
    "compile_chapter_04",
    "compiled_resource_store",
    "upsert_chapter_index",
    "write_teaching_index",
    "validate_compiled_resources",
]


if __name__ == "__main__":
    raise SystemExit(main())
