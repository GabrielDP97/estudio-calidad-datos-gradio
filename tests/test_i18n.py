"""Presentation localization must preserve values, contracts and session isolation."""
from concurrent.futures import ThreadPoolExecutor
import unittest

from quality_studio.i18n import CATALOG, language, tr
from quality_studio.ui import frame


class TranslationTests(unittest.TestCase):
    def test_catalog_has_all_three_languages_and_matching_placeholders(self):
        import re
        for source, translations in CATALOG.items():
            self.assertEqual(set(translations), {"es", "en", "de"})
            placeholders = set(re.findall(r"\{\w+\}", source))
            for translated in translations.values():
                self.assertTrue(translated)
                self.assertEqual(set(re.findall(r"\{\w+\}", translated)), placeholders)

    def test_templates_round_trip_without_translating_user_names_or_hashes(self):
        original = "Regla no válida en Fecha."
        english = tr(original, "en")
        self.assertEqual(english, "Invalid rule in Fecha.")
        self.assertEqual(tr(english, "de"), "Ungültige Regel in Fecha.")
        self.assertEqual(tr(tr(english, "de"), "es"), original)
        self.assertEqual(tr("user CSV content / Fecha", "de"), "user CSV content / Fecha")

    def test_csv_column_names_and_values_are_never_translated(self):
        context = language.set("de")
        try:
            component = frame(["Fecha", "Valor"], [["Texto", "Proyecto"]], translate=False)
            self.assertEqual(component.headers, ["Fecha", "Valor"])
            self.assertEqual(component.value["data"], [["Texto", "Proyecto"]])
        finally:
            language.reset(context)

    def test_concurrent_languages_do_not_leak(self):
        def translate(code):
            context = language.set(code)
            try:
                return tr("Proyecto")
            finally:
                language.reset(context)
        with ThreadPoolExecutor(max_workers=3) as pool:
            self.assertEqual(list(pool.map(translate, ["es", "en", "de"])), ["Proyecto", "Project", "Projekt"])
        self.assertEqual(language.get(), "es")
