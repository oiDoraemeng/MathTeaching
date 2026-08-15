"""合并视口刷新触发事件的测试。"""

import unittest

from ui.designer_window import MainWindow


class FakeTimer:
    def __init__(self) -> None:
        self.start_count = 0

    def start(self) -> None:
        self.start_count += 1


class ViewportRefreshTests(unittest.TestCase):
    def test_continuous_interaction_starts_one_pending_refresh(self) -> None:
        window = object.__new__(MainWindow)
        window._viewport_refreshing = False
        window._viewport_refresh_pending = False
        window._viewport_refresh_timer = FakeTimer()

        MainWindow._queue_viewport_refresh(window)
        MainWindow._queue_viewport_refresh(window)

        self.assertTrue(window._viewport_refresh_pending)
        self.assertEqual(window._viewport_refresh_timer.start_count, 1)


if __name__ == "__main__":
    unittest.main()
