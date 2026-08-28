from copy import deepcopy
import json
from pathlib import Path
import pytest
from ui.tokens import TokenError, build_qss, flatten_theme, load_tokens

RETIRED_SELECTORS = ("#agentPanel", "#agentCollapsedBar", "#agentUserBubble", "#agentAssistantBubble", "#agentPlanCard")
RETIRED_COLORS = ("#d9dde3", "#d0d7df", "#cbd3dd", "#dfe3e8", "#e0e5ea", "#3794ff", "#006ab1")


def _normalized_qss(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.splitlines()).rstrip() + "\n"

@pytest.mark.parametrize("theme", ["light", "dark"])
def test_qss_template_is_fully_substituted(theme: str) -> None:
    qss = build_qss(theme)
    assert "$" not in qss
    assert "#viewportToolbar" in qss
    assert "QLineEdit:focus" in qss
    assert "min-height: 32px" in qss


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_qss_has_required_and_no_retired_content(theme: str) -> None:
    qss = build_qss(theme).lower()
    assert "#scenesettingspanel" in qss
    assert not any(selector.lower() in qss for selector in RETIRED_SELECTORS)
    assert not any(color in qss for color in RETIRED_COLORS)


@pytest.mark.parametrize(
    ("label", "mutate", "error_path"),
    [
        ("missing theme leaf", lambda data: data["themes"]["dark"]["bg"].pop("scene"), r"^themes\.dark\.bg\.scene$"),
        ("mismatched theme key sets", lambda data: data["themes"]["dark"]["bg"].__setitem__("extra", "#fff"), r"^themes\.light\.bg\.extra$"),
        ("zero font size", lambda data: data["font"]["size"].__setitem__("title", 0), "font.size.title"),
        ("negative duration", lambda data: data["motion"]["duration"].__setitem__("normal", -1), "motion.duration.normal"),
        ("invalid color", lambda data: data["themes"]["light"]["bg"].__setitem__("scene", "not-a-color"), "themes.light.bg.scene"),
    ],
)
def test_malformed_token_matrix(tmp_path, label, mutate, error_path):
    data = deepcopy(load_tokens())
    mutate(data)
    path = tmp_path / f"{label.replace(' ', '_')}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TokenError, match=error_path):
        load_tokens(path)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_qss_matches_normalized_snapshot(theme: str) -> None:
    snapshot = (Path(__file__).parent / "snapshots" / f"base-{theme}.qss").read_text(encoding="utf-8")
    assert _normalized_qss(build_qss(theme)) == _normalized_qss(snapshot)

def test_light_and_dark_themes_have_identical_leaf_keys():
    tokens = load_tokens(); light = flatten_theme("light", tokens); dark = flatten_theme("dark", tokens)
    themed = {key for key in light if key.startswith(("bg_", "text_", "border_", "accent_", "status_", "shadow_"))}
    assert themed == {key for key in dark if key.startswith(("bg_", "text_", "border_", "accent_", "status_", "shadow_"))}
    assert light["bg_scene"] == "#f4f6f9"; assert dark["bg_scene"] == "#1e1f23"

def test_invalid_color_fails_fast(tmp_path):
    data = deepcopy(load_tokens()); data["themes"]["dark"]["accent"]["default"] = "not-a-color"
    path = tmp_path / "tokens.json"; path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TokenError, match="themes.dark.accent.default"): load_tokens(path)

@pytest.mark.parametrize("path_key", ["font", "space", "radius", "motion", "themes"])
def test_missing_or_wrong_sections_fail(tmp_path, path_key):
    data = deepcopy(load_tokens()); data[path_key] = None
    path = tmp_path / "tokens.json"; path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TokenError): load_tokens(path)

def test_flattened_names_and_invalid_theme():
    flat = flatten_theme("light")
    assert flat["size_title"] == 15 and flat["duration_normal"] == 150
    assert flat["easing_out"] and flat["shadow_overlay"]
    with pytest.raises(TokenError): flatten_theme("sepia")

def test_theme_shape_and_shadow_validation(tmp_path):
    data = deepcopy(load_tokens()); data["themes"]["dark"]["shadow"]["overlay"] = ""
    path = tmp_path / "tokens.json"; path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TokenError, match="shadow.overlay"): load_tokens(path)

@pytest.mark.parametrize("shadow", ["0 1px rgba(0,0,0,.4", "0 1px rgba(0,0,0,2)"])
def test_malformed_shadow_color_fails(tmp_path, shadow):
    data = deepcopy(load_tokens()); data["themes"]["dark"]["shadow"]["overlay"] = shadow
    path = tmp_path / "tokens.json"; path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TokenError, match="shadow.overlay"): load_tokens(path)
