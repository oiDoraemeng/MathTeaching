"""Review CLI refuses non-interactive approval."""

from __future__ import annotations

import pytest

from scripts.review_linear_algebra_teaching import main


def test_review_cli_requires_interactive_confirmation() -> None:
    with pytest.raises(SystemExit) as raised:
        main(
            [
                "--store-root",
                "out",
                "--topic",
                "ch02.matrix.composition",
                "--revision",
                "1",
                "--reviewer",
                "teacher",
                "--decision",
                "review",
            ]
        )
    assert raised.value.code == 2
