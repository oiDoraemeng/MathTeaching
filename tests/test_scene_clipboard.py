from dataclasses import dataclass

import pytest

from services.scene_clipboard import make_payload, parse_payload, paste_objects


@dataclass
class Point:
    name: str
    x: float
    y: float
    id: str


def test_parse_payload_rejects_invalid_utf8_as_value_error():
    with pytest.raises(ValueError, match="invalid clipboard payload"):
        parse_payload(b"\xff")


def test_paste_objects_skips_existing_ids(monkeypatch):
    source = Point("A", 1, 2, "source")
    payload = make_payload([source])
    generated = iter(("taken", "fresh"))
    monkeypatch.setattr("services.scene_clipboard.uuid4", lambda: type("U", (), {"hex": next(generated)})())

    pasted = paste_objects(
        payload,
        point_cls=Point,
        linear_cls=Point,
        annotation_cls=Point,
        existing_ids={"taken"},
    )

    assert pasted[0].id == "fresh"


def test_parse_payload_rejects_duplicate_object_ids():
    payload = '{"version":1,"objects":[{"type":"point","data":{"id":"dup","name":"A","x":0,"y":0}},{"type":"point","data":{"id":"dup","name":"B","x":1,"y":1}}]}'
    with pytest.raises(ValueError, match="duplicate clipboard object id"):
        parse_payload(payload)
