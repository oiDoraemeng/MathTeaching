from types import SimpleNamespace

from models.linear_algebra_cases import linear_algebra_case
from services.scene_commands import CommandPlan
from ui.designer_window import MainWindow


def test_case_plan_clears_before_loading_the_case_operations() -> None:
    case = linear_algebra_case("vector-subtraction")
    assert case is not None

    plan = MainWindow._linear_algebra_case_plan(case)

    assert isinstance(plan, CommandPlan)
    assert plan.scene == "2d"
    assert plan.operations[0] == {"op": "scene.clear", "scope": "all"}
    assert plan.operations[1:] == case.plan.operations


def test_unknown_case_reports_error_without_executing() -> None:
    statuses: list[tuple[str, bool]] = []
    window = MainWindow.__new__(MainWindow)
    window.algebra_panel = SimpleNamespace(set_status=lambda text, is_error=False: statuses.append((text, is_error)))
    window._load_linear_algebra_case("missing")

    assert statuses and statuses[-1][1] is True
