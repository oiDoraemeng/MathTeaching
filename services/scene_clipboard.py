"""Clipboard serialization and paste support for 2-D scene objects."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from uuid import uuid4

MAX_CLIPBOARD_BYTES = 1_000_000
VERSION = 1
_FIELDS = {
    "point": ("name", "x", "y", "visible", "color", "agent_alias"),
    "line": ("name", "kind", "start_point_id", "end_point_id", "visible", "color", "line_width", "style", "role", "label", "agent_alias"),
    "segment": ("name", "kind", "start_point_id", "end_point_id", "visible", "color", "line_width", "style", "role", "label", "agent_alias"),
    "ray": ("name", "kind", "start_point_id", "end_point_id", "visible", "color", "line_width", "style", "role", "label", "agent_alias"),
    "vector": ("name", "kind", "start_point_id", "end_point_id", "visible", "color", "line_width", "style", "role", "label", "agent_alias"),
    "annotation": ("name", "text", "x", "y", "latex", "visible", "color", "offset_x", "offset_y", "agent_alias"),
    "function": ("name", "kind", "expression", "parameters", "latex", "builtin_id", "visible", "color", "line_width", "range_scale", "agent_alias"),
    "curve": ("name", "kind", "expression", "parameters", "latex", "builtin_id", "visible", "color", "line_width", "range_scale", "agent_alias"),
}

def _plain(obj):
    return asdict(obj) if is_dataclass(obj) else dict(obj)

def make_payload(objects, *, max_bytes: int = MAX_CLIPBOARD_BYTES) -> str:
    records = []
    for obj in objects:
        data = _plain(obj)
        kind = data.get("kind", "annotation" if "text" in data else ("function" if "expression" in data else "point"))
        fields = _FIELDS.get(kind)
        if fields is None: raise ValueError(f"unsupported clipboard object: {kind}")
        records.append({"type": kind, "data": {**({"id": data["id"]} if "id" in data else {}), **{k: data[k] for k in fields if k in data}}})
    payload = {"version": VERSION, "objects": records}
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(text.encode("utf-8")) > max_bytes: raise ValueError("clipboard payload exceeds size limit")
    return text

def parse_payload(payload, *, max_bytes: int = MAX_CLIPBOARD_BYTES) -> dict:
    if isinstance(payload, bytes):
        if len(payload) > max_bytes: raise ValueError("clipboard payload exceeds size limit")
        payload = payload.decode("utf-8")
    if not isinstance(payload, str) or len(payload.encode("utf-8")) > max_bytes: raise ValueError("invalid clipboard payload")
    value = json.loads(payload)
    if type(value) is not dict or set(value) != {"version", "objects"} or type(value.get("version")) is not int or value.get("version") != VERSION or type(value.get("objects")) is not list: raise ValueError("unsupported clipboard payload")
    for rec in value["objects"]:
        if type(rec) is not dict or set(rec) != {"type", "data"} or rec.get("type") not in _FIELDS or type(rec.get("data")) is not dict: raise ValueError("invalid clipboard object")
        if set(rec["data"]) - (set(_FIELDS[rec["type"]]) | {"id"}): raise ValueError("clipboard field is not permitted")
    return value

def paste_objects(payload, *, point_cls, linear_cls, annotation_cls, curve_cls=None, existing_ids=(), offset=(0, 0)):
    value = parse_payload(payload)
    idmap = {}; result = []
    for rec in value["objects"]: idmap[rec["data"].get("id")] = uuid4().hex
    for rec in value["objects"]:
        d = dict(rec["data"]); old = d.pop("id", None); new = idmap.get(old, uuid4().hex)
        if rec["type"] == "point": d.update(id=new, x=d["x"] + offset[0], y=d["y"] + offset[1]); result.append(point_cls(**d))
        elif rec["type"] == "annotation": d.update(id=new, x=d["x"] + offset[0], y=d["y"] + offset[1]); result.append(annotation_cls(**d))
        elif rec["type"] in {"function", "curve"}:
            if curve_cls is not None: d.update(id=new); result.append(curve_cls(**d))
        else: d.update(id=new, start_point_id=idmap.get(d["start_point_id"], d["start_point_id"]), end_point_id=idmap.get(d["end_point_id"], d["end_point_id"])); result.append(linear_cls(**d))
    return result

def rectangle_select(objects, rect):
    """Select points/annotations inside (x1,y1,x2,y2), inclusive."""
    x1,y1,x2,y2 = rect; lo_x,hi_x=sorted((x1,x2)); lo_y,hi_y=sorted((y1,y2))
    return [o for o in objects if (hasattr(o,"x") and lo_x <= o.x <= hi_x and lo_y <= o.y <= hi_y) or hasattr(o, "expression")]

class SceneClipboard:
    def __init__(self, *, max_bytes=MAX_CLIPBOARD_BYTES): self.max_bytes=max_bytes; self.payload=None; self.source_pane=None; self._repeat=0
    def copy(self, objects, *, pane_id=None): self.payload=make_payload(objects,max_bytes=self.max_bytes); self.source_pane=pane_id; self._repeat=0; return self.payload
    def paste(self, *, pane_id=None, **kwargs):
        if self.payload is None: return []
        same = pane_id is not None and pane_id == self.source_pane
        self._repeat += 1 if same else 0
        return paste_objects(self.payload, offset=(self._repeat, self._repeat) if same else (0,0), **kwargs)
