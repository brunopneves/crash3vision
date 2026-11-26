import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices, QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.i18n import tr
from app.ui.main_window import MainWindow
from app.ui.widgets.help_dialog import HelpDialog, REPOSITORY_URL
from app.version import __version__


class HelpMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()
        self.addCleanup(self.window.close)

    def test_file_actions_shortcuts_and_language_selection(self) -> None:
        window = self.window
        menus = window.menuBar().actions()
        self.assertEqual([menu.text() for menu in menus], ["Arquivo", "Idioma", "Ajuda"])
        file_actions = menus[0].menu().actions()
        self.assertEqual(
            [action.text() for action in file_actions if not action.isSeparator()],
            [tr(f"menu.{key}") for key in (
                "new", "load_project", "save_project",
                "export_overlay", "export_current_view", "export_report",
            )],
        )
        self.assertTrue(file_actions[3].isSeparator())
        window.show()
        QApplication.processEvents()
        for action, handler, standard_key in zip(
            file_actions,
            ("new_project", "load_project", "save_project"),
            (QKeySequence.StandardKey.New, QKeySequence.StandardKey.Open, QKeySequence.StandardKey.Save),
        ):
            shortcut = QKeySequence(standard_key)
            self.assertEqual(action.shortcut(), shortcut)
            with patch.object(window.io, handler) as call:
                QTest.keySequence(window, shortcut)
            call.assert_called_once_with()

        self.assertTrue(window._language_actions["pt"].isChecked())
        window._language_actions["en"].trigger()
        self.assertTrue(window._language_actions["en"].isChecked())
        self.assertFalse(window._language_actions["pt"].isChecked())
        self.assertEqual(window.menuBar().actions(), menus)
        self.assertEqual([menu.text() for menu in menus], ["File", "Language", "Help"])

    def test_help_actions_open_localized_selectable_content(self) -> None:
        window = self.window
        window.resize(640, 460)
        window.show()
        for language, expected in (
            ("pt", ("Como usar", "Metodologia CRASH3", "Atalhos e ferramentas", "Sobre o CRASH3Vision")),
            ("en", ("How to use", "CRASH3 methodology", "Shortcuts and tools", "About CRASH3Vision")),
        ):
            with self.subTest(language=language):
                window._language_actions[language].trigger()
                menu = window.menuBar().actions()[2].menu()
                actions = [action for action in menu.actions() if not action.isSeparator()]
                self.assertEqual(tuple(action.text() for action in actions), expected)
                content = {}

                def inspect_dialog(dialog):
                    dialog.show()
                    QApplication.processEvents()
                    browser = dialog.browser
                    self.assertTrue(browser.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse)
                    self.assertEqual(browser.horizontalScrollBar().maximum(), 0)
                    if dialog.windowTitle() == expected[1]:
                        for width in (600, 400):
                            dialog.resize(width, dialog.height())
                            QApplication.processEvents()
                            self.assertEqual(browser.horizontalScrollBar().maximum(), 0)
                            renderer = browser._equation_renderer
                            graphics = [
                                renderer._graphics(cursor.charFormat())
                                for cursor in browser._equation_cursors()
                            ]
                            self.assertEqual([number for _, _, number in graphics], ["(1)", "", "(2)"])
                            for svg, size, _ in graphics:
                                self.assertTrue(svg.isValid())
                                self.assertLessEqual(size.width(), browser.viewport().width() - 28)
                            self.assertEqual(graphics[0][0].defaultSize().width(), 425 if width == 600 else 274)
                    browser.selectAll()
                    content[dialog.windowTitle()] = browser.createMimeDataFromSelection().text()
                    if dialog.windowTitle() == expected[0]:
                        self.assertGreater(browser.verticalScrollBar().maximum(), 0)
                    dialog.close()

                with patch.object(HelpDialog, "exec", new=inspect_dialog):
                    for action in actions:
                        action.trigger()
                self.assertEqual(tuple(content), expected)
                self.assertIn("C1–C6", content[expected[0]])
                original_position = (
                    "cabe ao examinador estabelecer a posição estrutural original" if language == "pt"
                    else "examiner establishes the original structural position"
                )
                self.assertIn(original_position, content[expected[0]])
                for term in (
                    "(W/5)[(A/2)L + (B/6)Q + 5G](1 + tan²α)",
                    "C₁ + 2C₂ + 2C₃ + 2C₄ + 2C₅ + C₆",
                    "C₁C₂ + C₂C₃ + C₃C₄ + C₄C₅ + C₅C₆",
                    "A²/(2B)", "√(2E / m)",
                ):
                    self.assertIn(term, content[expected[1]])
                self.assertIn("Q / E", content[expected[2]])
                self.assertIn("Z / X", content[expected[2]])
                self.assertIn(f"CRASH3Vision {__version__}", content[expected[3]])
                self.assertIn("Bruno P. Neves", content[expected[3]])
                self.assertIn("PolyForm Noncommercial License 1.0.0", content[expected[3]])

    def test_help_links_use_urls_documented_in_the_repository(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertIn(REPOSITORY_URL, (root / "CITATION.cff").read_text(encoding="utf-8"))
        self.assertTrue((root / "docs" / "methodology.md").is_file())
        for topic, url in (
            ("about", REPOSITORY_URL),
            ("about", f"{REPOSITORY_URL}/blob/main/LICENSE"),
            ("methodology", f"{REPOSITORY_URL}/blob/main/docs/methodology.md"),
        ):
            with patch.object(QDesktopServices, "openUrl") as open_url:
                dialog = HelpDialog(topic, self.window, {})
                self.assertIn(f'href="{url}"', dialog.browser.toHtml())
                dialog.browser.anchorClicked.emit(QUrl(url))
                open_url.assert_called_once_with(QUrl(url))
                dialog.close()
