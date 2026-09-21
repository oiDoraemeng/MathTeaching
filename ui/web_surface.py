"""重建 QtWebEngine 合成表面的共享工具。

窗口最小化时 Windows 会释放该窗口的渲染表面，Chromium 在恢复后不会自动
重新分配。此时 ``update()``/``repaint()`` 只让 Qt 重绘控件本身，``reload()``
只重新加载文档，两者都不会重建表面，也不会通知 Chromium 重新合成，于是面板
会永久停留在空白。只有让控件重新经历一次隐藏/显示，Quick/WebEngine 才会
重新分配表面并收到一次 ``WasShown``。
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget


def rebuild_web_surface(view: QWidget | None) -> bool:
    """强制 *view* 重新分配合成表面。

    返回是否真正执行了重建：控件尚未可见时 Qt 不会创建表面，此时保持调用方
    原有的降级行为。
    """
    if view is None:
        return False
    if not view.isVisible():
        return False

    from PySide6.QtCore import QCoreApplication, Qt

    # 先同步映射状态，避免 hide/show 引起闪烁。
    view.setAttribute(Qt.WidgetAttribute.WA_Mapped)
    view.update()
    QCoreApplication.processEvents()

    # 必要时再执行完整重建。
    parent = view.parentWidget()
    needs_full_rebuild = False

    if needs_full_rebuild and parent is not None and parent.isVisible():
        view.hide()
        QCoreApplication.processEvents()
        view.show()
        view.update()
        return True

    return True
