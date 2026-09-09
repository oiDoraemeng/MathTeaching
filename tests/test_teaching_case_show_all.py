from types import SimpleNamespace

import pytest

from agent.web_protocol import parse_envelope
from ui.designer_window import MainWindow
from ui.scene_pane_manager import ScenePaneManager


@pytest.mark.parametrize("topic_id, case_count", [("ch01.ops.addition", 3), ("other-lecture", 6)])
def test_web_show_all_reaches_unified_panes_without_legacy_grid(topic_id, case_count):
    manager = ScenePaneManager()
    manager.set_layout(4)
    user_ids = manager.visible_pane_ids()
    stale = manager.register_case("previous-lecture-case")
    case_refs = [f"{topic_id}:{i}" for i in range(case_count)]
    cases = [manager.register_case(ref) for ref in case_refs]
    manager.enter_lecture(case_refs[0], case_refs)
    host = SimpleNamespace(
        pane_manager=manager,
        _active_linear_algebra_topic_id=topic_id,
        _teaching_case_pane_ids=cases,
        _teaching_case_pane_grid=None,
        _agent_processed_requests={},
        _agent_session_store=SimpleNamespace(get_session=lambda _: None),
        agent_panel=SimpleNamespace(active_session_id="s", set_active_session=lambda _: None),
        _sync_layout_buttons=lambda: None,
    )
    host._set_teaching_case_pane_count = lambda count: MainWindow._set_teaching_case_pane_count(host, count)
    def dispatch(case_id, request):
        MainWindow._dispatch_agent_web_intent(host, parse_envelope({
            "protocol_version": 1, "type": "set_math_case_pane_count", "request_id": request,
            "session_id": "s", "payload": {"case_id": case_id, "pane_count": min(4, case_count)},
        }))
    dispatch("previous-lecture", "stale")
    assert manager.visible_pane_ids() == (cases[0],)
    dispatch(topic_id, "show-all")
    assert manager.visible_pane_ids() == tuple(cases[:4])
    assert stale not in manager.visible_pane_ids()
    assert all(pid not in manager.visible_pane_ids() for pid in user_ids)
