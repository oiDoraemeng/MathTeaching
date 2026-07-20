"""应用程序入口。"""

import sys

from PySide6.QtWidgets import QApplication

from ui.designer_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
