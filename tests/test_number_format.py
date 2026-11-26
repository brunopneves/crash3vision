import unittest

from app.core.number_format import format_display_number, format_float, parse_float
from app.i18n import get_language, set_language


class NumberFormatTests(unittest.TestCase):
    def test_display_grouping_and_precision_in_both_languages(self) -> None:
        for value, decimals, pt, en in (
            (1234567.891, 2, "1.234.567,89", "1,234,567.89"),
            (-1234.567, 2, "-1.234,57", "-1,234.57"),
            (0.002168, 6, "0,002168", "0.002168"),
            (4567, 0, "4.567", "4,567"),
            (0.0, 3, "0,000", "0.000"),
        ):
            with self.subTest(value=value):
                self.assertEqual(format_display_number(value, decimals, language="pt"), pt)
                self.assertEqual(format_display_number(value, decimals, language="en"), en)
        self.assertEqual(format_display_number(None), "—")
        self.assertEqual(
            format_display_number(0.0021731234, 6, significant_digits=True, language="pt"),
            "0,00217312",
        )
        self.assertEqual(
            format_display_number(1234.123456789, None, language="pt"), "1234,123456789"
        )

    def test_existing_parsing_and_report_format_are_preserved(self) -> None:
        self.addCleanup(set_language, get_language())
        for language, report_text in (("pt", "1234,50"), ("en", "1234.50")):
            set_language(language)
            self.assertEqual(format_float(1234.5), report_text)
            self.assertEqual(parse_float(format_display_number(1234.5)), 1234.5)
            self.assertEqual(parse_float("1.234,50"), 1234.5)
            self.assertEqual(parse_float("1,234.50"), 1234.5)
            self.assertEqual(parse_float("0,125"), 0.125)
