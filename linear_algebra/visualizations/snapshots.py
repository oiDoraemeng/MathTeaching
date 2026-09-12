"""Stable metadata snapshots for published teaching visualizations."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import hashlib
from typing import TYPE_CHECKING, Mapping

from linear_algebra.teaching.model import TeachingArtifact

from .contracts import VisualContract

if TYPE_CHECKING:
    from .compiler import CompiledVisualization


_TOPIC = re.compile(r"^ch\d{2}\.[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class CompiledSnapshot:
    schema_version: int
    topic_id: str
    artifact_revision: int
    source_hash: str
    compiler_version: str
    render_profile: str
    plan_digest: str
    stage_ids: tuple[str, ...]
    required_entity_roles: tuple[str, ...]
    required_relations: tuple[str, ...]
    invariants: tuple[str, ...]
    contract_digest: str = ""
    scene_family: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "topic_id": self.topic_id,
            "artifact_revision": self.artifact_revision,
            "source_hash": self.source_hash,
            "compiler_version": self.compiler_version,
            "render_profile": self.render_profile,
            "plan_digest": self.plan_digest,
            "stage_ids": list(self.stage_ids),
            "required_entity_roles": list(self.required_entity_roles),
            "required_relations": list(self.required_relations),
            "invariants": list(self.invariants),
            "contract_digest": self.contract_digest,
            "scene_family": self.scene_family,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "CompiledSnapshot":
        def strings(name: str) -> tuple[str, ...]:
            value = payload.get(name, ())
            if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
                raise ValueError(f"{name} must be an array of strings")
            return tuple(value)

        return cls(
            schema_version=int(payload.get("schema_version", 1)),
            topic_id=str(payload["topic_id"]),
            artifact_revision=int(payload["artifact_revision"]),
            source_hash=str(payload["source_hash"]),
            compiler_version=str(payload["compiler_version"]),
            render_profile=str(payload["render_profile"]),
            plan_digest=str(payload["plan_digest"]),
            stage_ids=strings("stage_ids"),
            required_entity_roles=strings("required_entity_roles"),
            required_relations=strings("required_relations"),
            invariants=strings("invariants"),
            contract_digest=str(payload.get("contract_digest", "")),
            scene_family=str(payload.get("scene_family", "")),
        )


def contract_digest_for(contract: VisualContract) -> str:
    payload: dict[str, object] = {
        "topic_id": contract.topic_id,
        "required_claims": contract.required_claims,
        "required_entity_roles": contract.required_entity_roles,
        "required_relations": contract.required_relations,
        "required_primitives": contract.required_primitives,
        "minimum_stage_count": contract.minimum_stage_count,
        "required_invariants": contract.required_invariants,
        "distinguishable_role_groups": contract.distinguishable_role_groups,
    }
    # Extended typed contract fields are included only when populated so the
    # established Chapter 1--3 digests remain stable while Chapter 4's digest
    # covers its exact roles, endpoints, parameters, and operation witnesses.
    for name in (
        "required_role_types",
        "required_relation_endpoints",
        "required_relation_kinds",
        "required_parameters",
        "expected_operations",
    ):
        value = getattr(contract, name)
        if value:
            payload[name] = value
    return "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True, default=list).encode("utf-8")).hexdigest()


def snapshot_from(
    artifact: TeachingArtifact, contract: VisualContract, compiled: "CompiledVisualization"
) -> CompiledSnapshot:
    if artifact.status != "published":
        raise ValueError("compiled snapshots require a published artifact")
    invariants = tuple(
        sorted(
            {
                invariant
                for stage in artifact.visual_semantics.stages
                for invariant in stage.expected_invariants
            }
        )
    )
    contract_digest = contract_digest_for(contract)
    return CompiledSnapshot(
        schema_version=1,
        topic_id=artifact.topic_id,
        artifact_revision=artifact.revision,
        source_hash=artifact.source.source_hash,
        compiler_version=compiled.compiler_version,
        render_profile=compiled.render_profile,
        plan_digest=compiled.plan_digest,
        stage_ids=tuple(stage.id for stage in compiled.storyboard),
        required_entity_roles=contract.required_entity_roles,
        required_relations=contract.required_relations,
        invariants=invariants,
        contract_digest=contract_digest,
        scene_family=artifact.visual_semantics.scene_family,
    )


class CompiledSnapshotStore:
    """Filesystem store for deterministic published snapshot metadata."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def save(self, snapshot: CompiledSnapshot) -> Path:
        path = self.path_for(snapshot.topic_id, snapshot.artifact_revision)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
        return path

    def load(self, topic_id: str, revision: int | None = None) -> CompiledSnapshot | None:
        if revision is None:
            candidates = sorted(self._topic_dir(topic_id).glob("r*.json"))
            if not candidates:
                return None
            path = candidates[-1]
        else:
            path = self.path_for(topic_id, revision)
        if not path.is_file():
            return None
        return CompiledSnapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def path_for(self, topic_id: str, revision: int) -> Path:
        if not _TOPIC.fullmatch(topic_id):
            raise ValueError("unsafe topic id")
        if revision < 1:
            raise ValueError("revision must be positive")
        chapter, _ = topic_id.split(".", 1)
        return self.root / chapter / topic_id / f"r{revision}.json"

    def _topic_dir(self, topic_id: str) -> Path:
        return self.path_for(topic_id, 1).parent


__all__ = ["CompiledSnapshot", "CompiledSnapshotStore", "contract_digest_for", "snapshot_from"]
