"""轻量级本地学习记忆，使用 QSettings 保存 JSON。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any, Mapping

from PySide6.QtCore import QSettings


@dataclass
class MemoryProfile:
    level: str = "high_school"
    prefer_visual: bool = True
    language: str = "zh-CN"
    recent_topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "MemoryProfile":
        value = value or {}
        topics = value.get("recent_topics", [])
        if not isinstance(topics, list):
            topics = []
        return cls(
            level=str(value.get("level", cls.level)),
            prefer_visual=bool(value.get("prefer_visual", cls.prefer_visual)),
            language=str(value.get("language", cls.language)),
            recent_topics=[str(topic) for topic in topics if str(topic).strip()][:20],
        )


class MemoryStore:
    """不记录原始聊天内容，只保存可解释的学习偏好和主题。"""

    KEY = "agent/memory/profile"
    LEGACY_KEY = "agent/memory"

    def __init__(self, settings: QSettings | None = None) -> None:
        self.settings = settings or QSettings("Math3DTeaching", "Math3DTeaching")

    def load(self) -> MemoryProfile:
        raw = self.settings.value(self.KEY, self.settings.value(self.LEGACY_KEY, ""))
        if isinstance(raw, dict):
            return MemoryProfile.from_mapping(raw)
        try:
            payload = json.loads(str(raw)) if raw else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}
        return MemoryProfile.from_mapping(payload if isinstance(payload, dict) else {})

    get_profile = load

    def save(self, profile: MemoryProfile | Mapping[str, Any]) -> MemoryProfile:
        normalized = profile if isinstance(profile, MemoryProfile) else MemoryProfile.from_mapping(profile)
        self.settings.setValue(self.KEY, json.dumps(normalized.to_dict(), ensure_ascii=False))
        self.settings.setValue(self.LEGACY_KEY, json.dumps(normalized.to_dict(), ensure_ascii=False))
        self.settings.sync()
        return normalized

    def update(self, **changes: Any) -> MemoryProfile:
        current = self.load().to_dict()
        current.update(changes)
        return self.save(current)

    def remember_topic(self, topic: str) -> MemoryProfile:
        topic = str(topic).strip()
        if not topic:
            return self.load()
        profile = self.load()
        topics = [item for item in profile.recent_topics if item != topic]
        topics.insert(0, topic)
        profile.recent_topics = topics[:20]
        return self.save(profile)

    def clear(self) -> None:
        self.settings.remove(self.KEY)
        self.settings.remove(self.LEGACY_KEY)
        self.settings.sync()
