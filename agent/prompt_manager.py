"""教学提示词模板管理。"""

from __future__ import annotations

from pathlib import Path
import re


class PromptManager:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else Path(__file__).parent / "prompts"

    def load(self, name: str) -> str:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "", str(name))
        if not safe_name:
            raise ValueError("提示词名称不能为空")
        path = self.root / f"{safe_name}.md"
        try:
            return path.read_text(encoding="utf-8")
        except OSError as error:
            raise KeyError(f"未知提示词模板: {name}") from error

    get_template = load

    def select(self, request: str) -> tuple[str, ...]:
        text = str(request).lower()
        names: list[str] = []
        if any(word in text for word in ("证明", "prove", "proof", "推导")):
            names.append("prove")
        if any(word in text for word in ("画", "绘制", "图形", "可视", "visual", "面积")):
            names.append("visualize")
        if not names or "teach" not in names:
            names.insert(0, "teach")
        return tuple(dict.fromkeys(names))

    def compose(self, names: tuple[str, ...] | list[str], **values: object) -> str:
        chunks = []
        for name in names:
            template = self.load(name)
            for key, value in values.items():
                template = template.replace("{{" + key + "}}", str(value))
            chunks.append(template.strip())
        return "\n\n".join(chunk for chunk in chunks if chunk)
