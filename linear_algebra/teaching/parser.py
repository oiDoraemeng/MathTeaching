"""Strict parsing and boundary checks for explanation-agent replies.

The provider is allowed to return mathematical prose and typed visual
semantics only.  This module keeps the trust boundary before model decoding:
the complete JSON tree is inspected for executable protocol leakage, then the
artifact schema and closed-reference validators normalize it into the immutable
teaching model.
"""

from __future__ import annotations

import json
import re
from typing import Mapping

from .model import TeachingArtifact
from .validation import ArtifactValidationError, validate_artifact_payload


FORBIDDEN_KEYS = frozenset({"op", "operations", "command_plan", "python", "html", "qt"})
FORBIDDEN_TEXT = re.compile(
    r"(?:geometry\.|linear(?:3d)?\.|CommandPlan|PySide6|PyVista|<script)",
    re.IGNORECASE,
)

_MAX_DEPTH = 32
_MAX_NODES = 4096
_MAX_STRING_LENGTH = 32_768


class AgentReplyError(ValueError):
    """A bounded, user-visible reason why a provider reply was not accepted."""

    def __init__(self, code: str, detail: str, *, issues: tuple[object, ...] = ()) -> None:
        self.code = code
        self.detail = detail
        self.issues = issues
        super().__init__(f"{code}: {detail}")


def parse_agent_reply(raw_reply: str, expected_topic_id: str) -> TeachingArtifact:
    """Parse exactly one safe artifact for ``expected_topic_id``.

    Markdown fences, executable operation names, schema failures, dangling
    references, and topic mismatches are rejected before a draft can be built.
    """

    if not isinstance(raw_reply, str):
        raise AgentReplyError("invalid_reply", "reply must be text")
    if not raw_reply.strip():
        raise AgentReplyError("invalid_json", "reply is empty")
    if raw_reply.lstrip().startswith("```"):
        raise AgentReplyError("markdown_fence", "reply must be a bare JSON object")

    try:
        payload = json.loads(raw_reply)
    except json.JSONDecodeError as error:
        raise AgentReplyError("invalid_json", error.msg) from error
    if not isinstance(payload, dict):
        raise AgentReplyError("invalid_root", "reply root must be an object")

    leakage = _find_forbidden(payload)
    if leakage is not None:
        code, detail = leakage
        raise AgentReplyError(code, detail)

    try:
        artifact = validate_artifact_payload(payload)
    except ArtifactValidationError as error:
        raise AgentReplyError(
            "artifact_invalid",
            str(error),
            issues=tuple(error.issues),
        ) from error
    except (TypeError, ValueError) as error:
        # 将普通模型错误统一为公开解析异常。
        raise AgentReplyError("artifact_invalid", str(error)) from error

    if artifact.topic_id != expected_topic_id:
        raise AgentReplyError(
            "topic_mismatch",
            f"topic_id {artifact.topic_id!r} does not match expected {expected_topic_id!r}",
        )
    return artifact


def _find_forbidden(payload: Mapping[str, object]) -> tuple[str, str] | None:
    """Scan every key and string value with bounded work and diagnostics."""

    nodes = 0

    def visit(value: object, path: str, depth: int) -> tuple[str, str] | None:
        nonlocal nodes
        nodes += 1
        if nodes > _MAX_NODES:
            return "reply_too_large", f"reply exceeds {_MAX_NODES} JSON values"
        if depth > _MAX_DEPTH:
            return "reply_too_deep", f"reply exceeds {_MAX_DEPTH} nested levels at {path}"
        if isinstance(value, str):
            if len(value) > _MAX_STRING_LENGTH:
                return "reply_too_large", f"string at {path} exceeds {_MAX_STRING_LENGTH} characters"
            if FORBIDDEN_TEXT.search(value):
                return "executable_leakage", f"forbidden executable text at {path}"
            return None
        if isinstance(value, Mapping):
            for key, child in value.items():
                if not isinstance(key, str):
                    return "invalid_key", f"JSON object key at {path} must be a string"
                if key.casefold() in FORBIDDEN_KEYS:
                    return "executable_leakage", f"forbidden key {key!r} at {path}"
                result = visit(child, f"{path}.{key}", depth + 1)
                if result is not None:
                    return result
            return None
        if isinstance(value, list):
            for index, child in enumerate(value):
                result = visit(child, f"{path}[{index}]", depth + 1)
                if result is not None:
                    return result
        return None

    return visit(payload, "$", 0)


__all__ = [
    "AgentReplyError",
    "FORBIDDEN_KEYS",
    "FORBIDDEN_TEXT",
    "parse_agent_reply",
]
