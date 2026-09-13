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
    assert "\\n\\n" not in meaning
    assert "\b" not in meaning
    assert "交换律" in refined["explanation"]["invariants"][0]


def test_vector_addition_refinement_aligns_visual_values_with_the_explanation() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.ops.addition"
    payload["visual_semantics"]["relations"][0]["id"] = "rel.0.claim.ch01.ops.addition"  # type: ignore[index]

    refined = refine_payload(payload)

    entities = {item["id"]: item for item in refined["visual_semantics"]["entities"]}
    assert entities["components_a"]["value"] == [3, 1]
    assert entities["components_b"]["value"] == [1, 2]
    assert entities["components_sum"]["value"] == [4, 3]
    assert [case["id"] for case in refined["explanation"]["case_layout"]["cases"]] == [
        "case.components",
        "case.geometry",
        "case.velocity",
    ]
    assert refined["explanation"]["case_layout"]["default_pane_count"] == 1


def test_vector_magnitude_refinement_uses_the_confirmed_two_case_reading() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.vector.magnitude"
    payload["claims"][0]["id"] = "claim.ch01.vector.magnitude"  # type: ignore[index]
    payload["visual_semantics"]["relations"][0]["id"] = "rel.magnitude.original"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert [example["id"] for example in explanation["worked_examples"]] == [
        "example.magnitude.nonzero",
        "example.magnitude.zero",
    ]
    assert [case["id"] for case in explanation["case_layout"]["cases"]] == [
        "case.magnitude.nonzero",
        "case.magnitude.zero",
    ]
    assert explanation["case_layout"]["default_pane_count"] == 1


def test_point_vector_distinction_refinement_uses_position_and_origin_cases() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.vector.point-distinction"
    payload["claims"][0]["id"] = "claim.ch01.vector.point-distinction"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert r"\boldsymbol v=x\boldsymbol e_1+y\boldsymbol e_2" in explanation["formula"]
    assert [example["id"] for example in explanation["worked_examples"]] == [
        "example.point-distinction.location",
        "example.point-distinction.vector",
    ]
    assert [case["id"] for case in explanation["case_layout"]["cases"]] == [
        "case.point-distinction.location",
        "case.point-distinction.vector",
    ]


def test_coordinate_system_refinement_keeps_only_the_lecture_standard_basis_case() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.vector.coordinate-system"
    payload["claims"][0]["id"] = "claim.ch01.vector.coordinate-system"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert explanation["formula"] == (
        r"\boldsymbol e_1=(1,0),\qquad \boldsymbol e_2=(0,1),\qquad "
        r"\lvert\boldsymbol e_1\rvert=\lvert\boldsymbol e_2\rvert=1,\qquad "
        r"\boldsymbol e_1\cdot\boldsymbol e_2=0"
    )
    assert [case["id"] for case in explanation["case_layout"]["cases"]] == [
        "case.coordinate-system.standard-basis",
    ]
    assert refined["visual_semantics"]["scene_kind"] == "2d"


def test_direction_examples_refinement_keeps_the_four_lecture_cases() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.vector.direction-examples"
    payload["claims"][0]["id"] = "claim.ch01.vector.direction-examples"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert [example["id"] for example in explanation["worked_examples"]] == [
        "example.direction.right-up",
        "example.direction.vertical",
        "example.direction.quadrants",
        "example.direction.northeast",
    ]
    assert [case["id"] for case in explanation["case_layout"]["cases"]] == [
        "case.direction-examples.1",
        "case.direction-examples.2",
        "case.direction-examples.3",
        "case.direction-examples.4",
    ]
    assert explanation["case_layout"]["default_pane_count"] == 1
    stages = refined["visual_semantics"]["stages"]
    assert stages[0]["input_entity_refs"] == ["direction_1_a"]
    assert stages[2]["input_entity_refs"] == ["direction_3_a", "direction_3_b"]


def test_vector_subtraction_refinement_uses_endpoint_difference_case() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.ops.subtraction"
    payload["claims"][0]["id"] = "claim.ch01.ops.subtraction"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert explanation["formula"] == r"\boldsymbol a-\boldsymbol b=(x_1-x_2,\,y_1-y_2)"
    assert explanation["worked_examples"][0]["result"] == [2.0, -1.0]
    assert explanation["case_layout"]["default_pane_count"] == 1
    assert refined["visual_semantics"]["relations"][0]["source_ref"] == "b"
    assert refined["visual_semantics"]["relations"][0]["target_ref"] == "a"


def test_vector_scalar_refinement_uses_the_four_lecture_effects() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.ops.scalar"
    payload["claims"][0]["id"] = "claim.ch01.ops.scalar"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert [example["kind"] for example in explanation["worked_examples"]] == ["scalar_multiple"] * 4
    assert [example["result"] for example in explanation["worked_examples"]] == [
        [2, 4], [1, 2], [-1, -2], [-2, 2]
    ]
    assert len(explanation["case_layout"]["cases"]) == 4
    assert refined["visual_semantics"]["scene_kind"] == "2d"


def test_composition_refinement_binds_both_endpoints_to_the_visual_graph() -> None:
    refined = refine_payload(composition_artifact_payload())

    entities = {item["id"]: item for item in refined["visual_semantics"]["entities"]}
    assert entities["y"]["value"] == [-2, 1]
    assert entities["z"]["value"] == [-1, 2]
    assert entities["B"]["value"] == [[0, -1], [1, 0]]
    assert "先 B 后 A" in {stage["title"] for stage in refined["visual_semantics"]["stages"]}
    assert "先 A 后 B" in {stage["title"] for stage in refined["visual_semantics"]["stages"]}
