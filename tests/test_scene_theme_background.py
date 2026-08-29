"""场景背景随应用有效主题变化的回归测试。"""

from models.scene_mode import SceneAppearance


def test_auto_background_uses_effective_theme() -> None:
    appearance = SceneAppearance()

    assert appearance.background == "auto"
    assert appearance.background_color("light") == "#f4f6f9"
    assert appearance.background_color("dark") == "#1e1f23"


def test_legacy_background_values_remain_explicit() -> None:
    assert SceneAppearance(background="light").background_color("dark") == "#f7f8fb"
    assert SceneAppearance(background="dark").background_color("light") == "#101317"
