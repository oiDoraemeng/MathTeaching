"""Safe model metadata shared by the Python projection and Web UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping
import json
from urllib.parse import urlsplit


@dataclass(frozen=True)
class ModelDescriptor:
    id: str
    name: str
    group: str
    provider: str
    protocol: str = "responses"
    capabilities: tuple[str, ...] = ()
    context_window: str = "128K"
    thinking_enabled: bool = True
    thinking_levels: tuple[str, ...] = ("Low", "High", "X-High")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["capabilities"] = list(self.capabilities)
        result["thinking_levels"] = list(self.thinking_levels)
        return result


BUILTIN_MODELS: tuple[ModelDescriptor, ...] = (
    ModelDescriptor(
        id="deepseek-v4-flash-high",
        name="Deepseek-V4-Flash High",
        group="builtin",
        provider="deepseek",
        capabilities=("reasoning",),
    ),
    ModelDescriptor(
        id="deepseek-v4-pro-high",
        name="Deepseek-V4-Pro High",
        group="builtin",
        provider="deepseek",
        capabilities=("image_input", "reasoning"),
        context_window="1M",
    ),
    ModelDescriptor(
        id="deepseek-v4-flash-vision-exp",
        name="deepseek-v4-flash-vision-exp",
        group="builtin",
        provider="deepseek",
        capabilities=("image_input", "reasoning"),
    ),
)


def model_catalog(custom: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, list[dict[str, Any]]]:
    builtins = [item.to_dict() for item in BUILTIN_MODELS]
    custom_rows: list[dict[str, Any]] = []
    for model_id, value in (custom or {}).items():
        row = dict(value)
        row.update({"id": model_id, "group": "custom"})
        row.setdefault("name", str(row.get("model", model_id)))
        row.pop("api_key", None)
        custom_rows.append(row)
    return {"builtin": builtins, "custom": custom_rows}


def default_model_id(selected: str | None, custom_ids: tuple[str, ...] = ()) -> str:
    available = {item.id for item in BUILTIN_MODELS}
    available.update(custom_ids)
    legacy = {"deepseek-chat", "DeepSeek"}
    return selected if selected in available or selected in legacy else BUILTIN_MODELS[0].id


def validate_provider_url(value: str) -> str:
    url = str(value or "").strip().rstrip("/")
    parsed = urlsplit(url)
    if len(url) > 512 or parsed.username or parsed.password or parsed.scheme not in {"https", "http"}:
        raise ValueError("invalid_provider_url")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("provider_url_must_use_https")
    if not parsed.netloc:
        raise ValueError("invalid_provider_url")
    return url


class CustomModelStore:
    """Versioned QSettings storage; raw keys never leave this class."""

    KEY = "agent/custom_models"

    @staticmethod
    def _settings():
        from PySide6.QtCore import QSettings
        return QSettings("Math3DTeaching", "Math3DTeaching")

    @classmethod
    def load(cls) -> dict[str, dict[str, Any]]:
        raw = cls._settings().value(cls.KEY, "{}")
        try:
            value = json.loads(str(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    @classmethod
    def save(cls, model_id: str, value: Mapping[str, Any]) -> None:
        model_id = str(model_id or "").strip()
        if not model_id or len(model_id) > 128:
            raise ValueError("invalid_model_id")
        row = dict(value)
        row["base_url"] = validate_provider_url(str(row.get("base_url", "")))
        row["model"] = str(row.get("model", "")).strip()
        if not row["model"]:
            raise ValueError("model_name_required")
        capabilities = set(str(item) for item in row.get("capabilities", []) if isinstance(item, str))
        for flag, capability in (("tools", "tools"), ("image_input", "image_input"), ("reasoning", "reasoning")):
            if bool(row.get(flag, False)):
                capabilities.add(capability)
        row["capabilities"] = sorted(capabilities)
        for field, allowed in (("input_context", {"", "32K", "64K", "128K", "256K"}), ("output_context", {"", "8K", "16K", "32K", "64K"})):
            if str(row.get(field, "")) not in allowed:
                raise ValueError(f"invalid_{field}")
        models = cls.load()
        if not row.get("api_key") and model_id in models:
            row["api_key"] = models[model_id].get("api_key", "")
        models[model_id] = row
        cls._settings().setValue(cls.KEY, json.dumps(models, ensure_ascii=False))
        cls._settings().sync()

    @classmethod
    def delete(cls, model_id: str) -> None:
        models = cls.load()
        models.pop(str(model_id), None)
        cls._settings().setValue(cls.KEY, json.dumps(models, ensure_ascii=False))
        cls._settings().sync()
