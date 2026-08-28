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
