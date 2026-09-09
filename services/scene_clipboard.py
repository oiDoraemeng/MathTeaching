"""Clipboard serialization and paste support for 2-D scene objects."""
from __future__ import annotations

import json
import math
from numbers import Real
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
        if "expression" in data:
            kind = "curve"
        else:
            kind = data.get("kind", "annotation" if "text" in data else "point")
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
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("invalid clipboard payload") from exc
    if not isinstance(payload, str) or len(payload.encode("utf-8")) > max_bytes: raise ValueError("invalid clipboard payload")
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid clipboard payload") from exc
    if type(value) is not dict or set(value) != {"version", "objects"} or type(value.get("version")) is not int or value.get("version") != VERSION or type(value.get("objects")) is not list: raise ValueError("unsupported clipboard payload")
    seen_ids = set()
    for rec in value["objects"]:
        if type(rec) is not dict or set(rec) != {"type", "data"} or rec.get("type") not in _FIELDS or type(rec.get("data")) is not dict: raise ValueError("invalid clipboard object")
        if set(rec["data"]) - (set(_FIELDS[rec["type"]]) | {"id"}): raise ValueError("clipboard field is not permitted")
        if "id" not in rec["data"]: raise ValueError("clipboard object missing id")
        object_id = rec["data"]["id"]
        if not isinstance(object_id, str) or not object_id:
            raise ValueError("clipboard object id must be a non-empty string")
        if object_id in seen_ids:
            raise ValueError("duplicate clipboard object id")
        seen_ids.add(object_id)
        for key, item in rec["data"].items():
            if isinstance(item, Real) and not isinstance(item, bool) and not math.isfinite(float(item)):
                raise ValueError("clipboard numeric field must be finite")
            if key in {"x", "y", "line_width", "offset_x", "offset_y", "range_scale"} and not isinstance(item, Real):
                raise ValueError("clipboard numeric field is invalid")
            if key in {"name", "kind", "expression", "text", "latex", "builtin_id", "color", "style", "role", "agent_alias", "start_point_id", "end_point_id"} and item is not None and not isinstance(item, str):
                raise ValueError("clipboard text field is invalid")
            if key == "visible" and not isinstance(item, bool):
                raise ValueError("clipboard visible field is invalid")
            if key == "parameters" and (not isinstance(item, dict) or any(not isinstance(k, str) or not isinstance(v, Real) or isinstance(v, bool) or not math.isfinite(float(v)) for k, v in item.items())):
                raise ValueError("clipboard parameters field is invalid")
    return value

def paste_objects(payload, *, point_cls, linear_cls, annotation_cls, curve_cls=None,
                  existing_ids=(), offset=(0, 0), max_bytes: int = MAX_CLIPBOARD_BYTES):
    value = parse_payload(payload, max_bytes=max_bytes)
    occupied = set(existing_ids)
    idmap = {}; result = []

    def new_id() -> str:
        candidate = uuid4().hex
        while candidate in occupied:
            candidate = uuid4().hex
        occupied.add(candidate)
        return candidate

    for rec in value["objects"]:
        idmap[rec["data"]["id"]] = new_id()
    for rec in value["objects"]:
        d = dict(rec["data"]); old = d.pop("id", None); new = idmap.get(old) or new_id()
        if rec["type"] == "point": d.update(id=new, x=d["x"] + offset[0], y=d["y"] + offset[1]); result.append(point_cls(**d))
        elif rec["type"] == "annotation": d.update(id=new, x=d["x"] + offset[0], y=d["y"] + offset[1]); result.append(annotation_cls(**d))
        elif rec["type"] in {"function", "curve"}:
            if curve_cls is not None: d.update(id=new); result.append(curve_cls(**d))
        else: d.update(id=new, start_point_id=idmap.get(d["start_point_id"], d["start_point_id"]), end_point_id=idmap.get(d["end_point_id"], d["end_point_id"])); result.append(linear_cls(**d))
    return result

def rectangle_select(objects, rect):
    """Select points/annotations inside (x1,y1,x2,y2), inclusive."""
    x1,y1,x2,y2 = rect; lo_x,hi_x=sorted((x1,x2)); lo_y,hi_y=sorted((y1,y2))
    ids = {getattr(o, "id", None): o for o in objects}
    selected = []
    for o in objects:
        if hasattr(o, "x") and lo_x <= o.x <= hi_x and lo_y <= o.y <= hi_y:
            selected.append(o); continue
        # Linear objects are selected when either endpoint, or the segment
        # bounding box, intersects the marquee.
        if hasattr(o, "start_point_id"):
            a, b = ids.get(o.start_point_id), ids.get(o.end_point_id)
            if a and b and not (max(a.x,b.x) < lo_x or min(a.x,b.x) > hi_x or max(a.y,b.y) < lo_y or min(a.y,b.y) > hi_y):
                selected.append(o); continue
        # Curves/functions span the plot domain; treat a marquee intersecting
        # the default domain as selecting the curve.  Objects may optionally
        # expose a finite bounding box for more precise hit testing.
        if hasattr(o, "expression"):
            bounds = getattr(o, "bounds", (-10.0, -10.0, 10.0, 10.0))
            bx1, by1, bx2, by2 = bounds
            if not (max(bx1, bx2) < lo_x or min(bx1, bx2) > hi_x or max(by1, by2) < lo_y or min(by1, by2) > hi_y):
                selected.append(o)
    return selected

class SceneClipboard:
    def __init__(self, *, max_bytes=MAX_CLIPBOARD_BYTES): self.max_bytes=max_bytes; self.payload=None; self.source_pane=None; self._repeat=0
    def copy(self, objects, *, pane_id=None): self.payload=make_payload(objects,max_bytes=self.max_bytes); self.source_pane=pane_id; self._repeat=0; return self.payload
    def paste(self, *, pane_id=None, **kwargs):
        if self.payload is None: return []
        same = pane_id is not None and pane_id == self.source_pane
        repeat = self._repeat + 1 if same else self._repeat
        result = paste_objects(self.payload, offset=(repeat, repeat) if same else (0, 0), max_bytes=self.max_bytes, **kwargs)
        self._repeat = repeat
        return result
