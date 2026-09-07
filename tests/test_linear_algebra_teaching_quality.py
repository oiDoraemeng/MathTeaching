from __future__ import annotations

from linear_algebra.teaching.quality import refine_payload
from tests.teaching_fixtures import composition_artifact_payload


def test_vector_addition_refinement_keeps_two_classic_geometric_readings() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.ops.addition"
    payload["explanation"]["worked_examples"] = [  # type: ignore[index]
        {
            "id": "example.addition",
            "title": "example",
            "kind": "vector_addition",
            "given": [[0, 0], [1, 1]],
            "calculation": [],
            "result": [1, 1],
            "checks": [],
            "claim_refs": ["claim.composition-order"],
        }
    ]

    refined = refine_payload(payload)

    meaning = refined["explanation"]["geometric_meaning"]
    assert "三角形法则" in meaning
    assert "平行四边形法则" in meaning


def test_vector_addition_refinement_aligns_visual_values_with_the_explanation() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.ops.addition"
    payload["visual_semantics"]["relations"][0]["id"] = "rel.0.claim.ch01.ops.addition"  # type: ignore[index]

    refined = refine_payload(payload)

    entities = {item["id"]: item for item in refined["visual_semantics"]["entities"]}
    assert entities["a"]["value"] == [2, 1]
    assert entities["b"]["value"] == [1, 3]
    assert entities["sum"]["value"] == [3, 4]
    assert refined["visual_semantics"]["relations"][0]["parameters"]["result"] == [3, 4]


def test_composition_refinement_binds_both_endpoints_to_the_visual_graph() -> None:
    refined = refine_payload(composition_artifact_payload())

    entities = {item["id"]: item for item in refined["visual_semantics"]["entities"]}
    assert entities["y"]["value"] == [-2, 1]
    assert entities["z"]["value"] == [-1, 2]
    assert entities["B"]["value"] == [[0, -1], [1, 0]]
    assert "先 B 后 A" in {stage["title"] for stage in refined["visual_semantics"]["stages"]}
    assert "先 A 后 B" in {stage["title"] for stage in refined["visual_semantics"]["stages"]}
