"""用户可编辑的 Agent 规则。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings


class InstructionStore:
    KEY = "agent/instructions/math_teacher"
    LEGACY_KEY = "agent/instructions"

    def __init__(self, root: str | Path | None = None, settings: QSettings | None = None) -> None:
        self.root = Path(root) if root is not None else Path(__file__).parent / "instructions"
        self.settings = settings or QSettings("Math3DTeaching", "Math3DTeaching")

    @property
    def default_text(self) -> str:
        path = self.root / "math_teacher.md"
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return "你是数学教学助手。\n\n1. 优先使用图形解释数学概念。\n2. 任何修改场景的操作必须生成 CommandPlan。\n3. 禁止执行未知代码。\n4. 禁止绕过 SceneCommandService。\n5. 复杂数学问题先解释，再生成图形。"

    def load(self) -> str:
        value = self.settings.value(self.KEY, self.settings.value(self.LEGACY_KEY, ""))
        return str(value) if str(value).strip() else self.default_text

    get = load

    def save(self, text: str) -> str:
        value = str(text).strip()
        if not value:
            value = self.default_text
        self.settings.setValue(self.KEY, value)
        self.settings.setValue(self.LEGACY_KEY, value)
        self.settings.sync()
        return value

    def reset(self) -> str:
        return self.save(self.default_text)
