from ui.scene_pane_manager import ScenePaneManager


def test_lecture_default_and_show_all_hide_user_panes():
    manager = ScenePaneManager()
    manager.set_layout(4)
    user_ids = manager.visible_pane_ids()
    cases = [manager.register_case(f"case-{i}", name=f"案例 {i}") for i in range(1, 4)]

    assert manager.enter_lecture("case-1") == (cases[0],)
    assert manager.visible_pane_ids() == (cases[0],)

    assert manager.show_all_cases() == tuple(cases)
    assert all(pid not in manager.visible_pane_ids() for pid in user_ids)

    assert manager.leave_lecture() == user_ids


def test_case_panes_are_retained_when_hidden():
    manager = ScenePaneManager()
    case_id = manager.register_case("vector-addition")
    manager.pane(case_id).scene_2d["objects"] = [{"id": "v"}]
    manager.enter_lecture("vector-addition")
    manager.leave_lecture()
    assert manager.pane(case_id).scene_2d["objects"] == [{"id": "v"}]


def test_lecture_scope_excludes_stale_cases_and_caps_show_all():
    manager = ScenePaneManager()
    current = [manager.register_case(f"current-{i}") for i in range(6)]
    stale = manager.register_case("stale")
    manager.enter_lecture("current-1", [f"current-{i}" for i in range(6)])
    shown = manager.show_all_cases()
    assert shown == tuple(current[:4])
    assert stale not in shown


def test_leave_without_enter_does_not_restore_all_user_panes():
    manager = ScenePaneManager()
    manager.set_layout(2)
    first = manager.visible_pane_ids()[0]
    manager.set_visible_panes([first])
    assert manager.leave_lecture() == (first,)
