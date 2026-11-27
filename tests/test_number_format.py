import unittest

from app.core.number_format import format_display_number, format_float, parse_float, relocalize_decimal_input
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

    def test_parsing_accepts_unambiguous_formats_in_both_languages(self) -> None:
        self.addCleanup(set_language, get_language())
        examples = (
            ("0,0149", 0.0149), ("0.0149", 0.0149), ("-0,0149", -0.0149),
            ("-1234.567", -1234.567), ("+1.234,50", 1234.5), ("-1,234.50", -1234.5),
            ("1.234.567", 1234567.0), ("1,234,567", 1234567.0),
            ("1 234,50", 1234.5), ("1\u202f234\u202f567", 1234567.0),
            ("1.2340", 1.234), ("1,2340", 1.234), ("0,", 0.0), (".5", 0.5),
            ("-1,234e-5", -1.234e-5), (" 179048,05781761295 ", 179048.05781761295),
        )
        for language in ("pt", "en"):
            set_language(language)
            for text, expected in examples:
                with self.subTest(language=language, text=text):
                    self.assertEqual(parse_float(text), expected)

    def test_three_decimal_digits_follow_the_selected_language(self) -> None:
        self.addCleanup(set_language, get_language())
        for language, native, alternate in (
            ("pt", "1,234", "1.234"),
            ("en", "1.234", "1,234"),
        ):
            with self.subTest(language=language):
                set_language(language)
                self.assertEqual(parse_float(native), 1.234)
                self.assertEqual(parse_float("-" + native), -1.234)
                self.assertEqual(parse_float(alternate + "0"), 1.234)
                with self.assertRaises(ValueError):
                    parse_float(alternate)

        set_language("en")
        self.assertEqual(relocalize_decimal_input("-1,234", "pt"), "-1.234")
        self.assertEqual(relocalize_decimal_input("1.234", "pt"), "1.234")

    def test_parsing_rejects_malformed_or_ambiguous_formats_in_both_languages(self) -> None:
        self.addCleanup(set_language, get_language())
        for language in ("pt", "en"):
            set_language(language)
            for text in (
                "1,8,00.00", "1.8.00,00", "18,00.00", "1,234.5.0",
                "1,,234", "1..234", "1.234.56",
                "12 34", "1  234", "1 234\u202f567", "1_800", "+ 1800",
                "NaN", "inf", "1e999", "1800 kg",
            ):
                with self.subTest(language=language, text=text):
                    with self.assertRaises(ValueError):
                        parse_float(text, default=0.0)
