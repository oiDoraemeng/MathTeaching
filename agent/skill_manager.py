"""数学 Skill 的发现、选择和 CommandPlan 生成。"""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib.util
from pathlib import Path
import re
from typing import Any, Callable

from services.scene_commands import CommandPlan, SceneCommandService


@dataclass(frozen=True)
class SkillManifest:
    name: str
    description: str = ""
    version: str = "1.0"
    triggers: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    path: Path | None = field(default=None, compare=False, repr=False)


@dataclass
class Skill:
    manifest: SkillManifest
    handler: Any

    def create_plan(self, request: str, context: object = None) -> CommandPlan | None:
        creator = getattr(self.handler, "create_plan", None)
        if not callable(creator):
            return None
        result = creator(request, context)
        if result is None:
            return None
        if not isinstance(result, CommandPlan):
            raise TypeError(f"Skill {self.manifest.name} 必须返回 CommandPlan")
        return result


class SkillManager:
    """只加载项目内 skills，handler 没有访问 Qt/PyVista 的权限。"""

    def __init__(self, root: str | Path | None = None, command_service: SceneCommandService | None = None) -> None:
        self.root = Path(root) if root is not None else Path(__file__).parent / "skills"
        self.fallback_root = Path(__file__).parent.parent / "skills"
        self.command_service = command_service or SceneCommandService()
        self.skills: dict[str, Skill] = {}
        self.reload()

    def reload(self) -> None:
        self.skills.clear()
        roots = [self.root]
        if self.root == Path(__file__).parent / "skills" and self.fallback_root.exists():
            roots.append(self.fallback_root)
        for current_root in roots:
            if not current_root.exists():
                continue
            for directory in sorted(item for item in current_root.iterdir() if item.is_dir()):
                manifest_path = directory / "skill.yaml"
                handler_path = directory / "handler.py"
                if not manifest_path.exists() or not handler_path.exists():
                    continue
                try:
                    manifest = SkillManifest(path=directory, **_read_manifest(manifest_path))
                    handler = _load_handler(handler_path, manifest.name)
                except (OSError, ValueError, TypeError, ImportError):
                    continue
                # agent/skills 是主实现；根目录 skills/ 只是兼容入口，不覆盖已发现的主 Skill。
                self.skills.setdefault(manifest.name, Skill(manifest, handler))

    def list_skills(self) -> tuple[SkillManifest, ...]:
        return tuple(skill.manifest for skill in self.skills.values())

    @property
    def available_skills(self) -> tuple[SkillManifest, ...]:
        return self.list_skills()

    def get(self, name: str) -> Skill:
        try:
            return self.skills[str(name)]
        except KeyError as error:
            raise KeyError(f"未知数学 Skill: {name}") from error

    get_skill = get

    def match(self, request: str) -> tuple[SkillManifest, ...]:
        text = str(request).lower()
        matched = []
        for skill in self.skills.values():
            words = skill.manifest.triggers or (skill.manifest.name,)
            if any(str(word).lower() in text for word in words):
                matched.append(skill.manifest)
        return tuple(matched)

    select_skill = match

    def create_plan(self, name: str, request: str, context: object = None) -> CommandPlan | None:
        plan = self.get(name).create_plan(request, context)
        if plan is not None:
            validation = self.command_service.preview(plan)
            if not validation.valid:
                raise ValueError("；".join(validation.messages))
        return plan

    def create_plan_for_request(self, request: str, context: object = None) -> tuple[SkillManifest, CommandPlan] | None:
        for manifest in self.match(request):
            plan = self.create_plan(manifest.name, request, context)
            if plan is not None:
                return manifest, plan
        return None


def _read_manifest(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-") and current_list:
            data.setdefault(current_list, []).append(line[1:].strip().strip("'\""))
            continue
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        if not value:
            current_list = key
            data[key] = []
            continue
        current_list = None
        value = value.strip("'\"")
        data[key] = value
    return {
        "name": str(data.get("name", path.parent.name)),
        "description": str(data.get("description", "")),
        "version": str(data.get("version", "1.0")),
        "triggers": tuple(str(item) for item in data.get("triggers", [])),
        "capabilities": tuple(str(item) for item in data.get("capabilities", [])),
    }


def _load_handler(path: Path, name: str) -> Any:
    module_name = f"math3d_skill_{re.sub(r'[^a-zA-Z0-9_]', '_', name)}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 Skill handler: {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    factory: Callable[[], Any] | None = getattr(module, "build_handler", None)
    return factory() if callable(factory) else module
