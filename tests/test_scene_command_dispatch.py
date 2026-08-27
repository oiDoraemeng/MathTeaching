from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

from ui.designer_window import _SceneCommandBridge, _SceneCommandHostProxy


class _RecordingHost:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object | None, QThread]] = []

    def begin_scene_command_transaction(self) -> None:
        self.calls.append(("begin", None, QThread.currentThread()))

    def apply_scene_command(self, operation: dict[str, object]) -> None:
        self.calls.append(("apply", operation, QThread.currentThread()))

    def commit_scene_command_transaction(self) -> None:
        self.calls.append(("commit", None, QThread.currentThread()))

    def rollback_scene_command_transaction(self) -> None:
        self.calls.append(("rollback", None, QThread.currentThread()))


class _FailingHost(_RecordingHost):
    def apply_scene_command(self, operation: dict[str, object]) -> None:
        super().apply_scene_command(operation)
        raise RuntimeError("scene mutation failed")


class _DispatchWorker(QObject):
    finished = Signal()
    failed = Signal(str)

    def __init__(self, proxy: _SceneCommandHostProxy) -> None:
        super().__init__()
        self.proxy = proxy

    @Slot()
    def run(self) -> None:
        try:
            self.proxy.begin_scene_command_transaction()
            self.proxy.apply_scene_command({"op": "point.upsert", "id": "P"})
            self.proxy.commit_scene_command_transaction()
        except Exception as error:  # pragma: no cover - assertion reports this
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


def test_scene_command_host_proxy_dispatches_scene_mutations_to_gui_thread() -> None:
    app = QApplication.instance() or QApplication([])
    host = _RecordingHost()
    bridge = _SceneCommandBridge(host)
    proxy = _SceneCommandHostProxy(bridge)
    worker_thread = QThread()
    worker = _DispatchWorker(proxy)
    worker.moveToThread(worker_thread)
    errors: list[str] = []
    worker_thread.started.connect(worker.run)
    worker.failed.connect(errors.append)
    worker.finished.connect(worker_thread.quit)
    worker.finished.connect(worker.deleteLater)
    worker_thread.finished.connect(app.quit)
    worker_thread.start()
    QTimer.singleShot(5000, app.quit)
    app.exec()
    worker_thread.wait(1000)

    assert not errors
    assert [(name, value) for name, value, _ in host.calls] == [
        ("begin", None),
        ("apply", {"op": "point.upsert", "id": "P"}),
        ("commit", None),
    ]
    assert all(thread == bridge.thread() for _, _, thread in host.calls)


def test_scene_command_host_proxy_rethrows_gui_thread_errors() -> None:
    app = QApplication.instance() or QApplication([])
    bridge = _SceneCommandBridge(_FailingHost())
    proxy = _SceneCommandHostProxy(bridge)
    worker_thread = QThread()
    worker = _DispatchWorker(proxy)
    worker.moveToThread(worker_thread)
    errors: list[str] = []
    worker_thread.started.connect(worker.run)
    worker.failed.connect(errors.append)
    worker.finished.connect(worker_thread.quit)
    worker.finished.connect(worker.deleteLater)
    worker_thread.finished.connect(app.quit)
    worker_thread.start()
    QTimer.singleShot(5000, app.quit)
    app.exec()
    worker_thread.wait(1000)

    assert errors == ["scene mutation failed"]
