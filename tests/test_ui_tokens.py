from copy import deepcopy
import json
import pytest
from ui.tokens import TokenError, flatten_theme, load_tokens

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
