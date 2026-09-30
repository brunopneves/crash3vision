import sys
import ctypes
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.version import __version__


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is not None:
        return str(Path(base_path) / relative_path)
    return str(Path(__file__).resolve().parents[1] / relative_path)


def main():
    app_id = f"crash3vision.app.{__version__}"
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    app = QApplication(sys.argv)

    icon_path = resource_path("app/assets/crash3_icon.ico")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    win = MainWindow()
    win.setWindowIcon(app_icon)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
