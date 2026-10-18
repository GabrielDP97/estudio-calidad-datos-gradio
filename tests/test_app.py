"""Prueba integral de Gradio a través de HTTP, sin sustituir los servicios reales."""
import json
import os
import socket
import tempfile
import unittest

os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

from gradio_client import Client, handle_file
from quality_studio.ui import build_app
from quality_studio.engine import digest
from pathlib import Path


class GradioIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        cls.app = build_app(cls.directory.name)
        cls.app.queue(default_concurrency_limit=1)
        cls.app.launch(server_name="127.0.0.1", server_port=port, share=False, prevent_thread_lock=True, quiet=True)
        cls.client = Client(f"http://127.0.0.1:{port}", verbose=False)

    @classmethod
    def tearDownClass(cls):
        cls.app.close()
        cls.directory.cleanup()

    def test_demo_preview_execution_downloads_and_persistent_history_via_http(self):
        workspace_update, _ = self.client.predict(api_name="/demo")
        workspace = workspace_update["value"]
        dataset_update, history, _, _ = self.client.predict(workspace, api_name="/select_workspace")
        self.assertEqual(len(dataset_update["choices"]), 2)
        dataset = dataset_update["value"]
        loaded = self.client.predict(dataset, api_name="/load_dataset")
        rules = loaded[0]
        self.assertIn("8 filas", loaded[4])
        preview = self.client.predict(dataset, rules, api_name="/preview")
        self.assertIn("Filas válidas", preview[2])
        self.assertEqual(len(preview[1].get("value", preview[1])["data"]), 8)
        first = self.client.predict(workspace, dataset, rules, api_name="/execute")
        report = json.loads(first[8])
        self.assertEqual(report["summary"]["clean_rows"], 3)
        self.assertEqual(len(first[5]), 5)
        self.assertEqual(digest(Path(first[5][0]).read_bytes()), report["output_sha256"])
        imported, _ = self.client.predict(dataset, handle_file(first[5][4]), api_name="/import_rules")
        self.assertEqual(json.loads(imported), json.loads(rules))
        exported, _ = self.client.predict(dataset, imported, api_name="/export_rules")
        self.assertEqual(json.loads(Path(exported).read_text(encoding="utf-8")), json.loads(rules))
        second = self.client.predict(workspace, dataset, rules, api_name="/execute")
        self.assertEqual(report["output_sha256"], json.loads(second[8])["output_sha256"])
        _, history, _, _ = self.client.predict(workspace, api_name="/select_workspace")
        self.assertEqual(len(history.get("value", history)["data"]), 2)

        other_dataset = dataset_update["choices"][1][1]
        other_view = self.client.predict(other_dataset, api_name="/load_dataset")
        self.assertEqual(other_view[12].get("value", other_view[12])["data"], [])
        self.assertEqual(other_view[13], "")
        saved_view = self.client.predict(dataset, rules, api_name="/save_rules")
        self.assertIn("Contrato guardado", saved_view[11])
        self.assertIn("8 filas", saved_view[4])


    def test_empty_project_and_no_selected_csv_have_valid_empty_views(self):
        workspace_update, _ = self.client.predict("Proyecto vacío", api_name="/create_workspace")
        datasets, _, _, _ = self.client.predict(workspace_update["value"], api_name="/select_workspace")
        self.assertIsNone(datasets["value"])
        view = self.client.predict(None, api_name="/load_dataset")
        self.assertEqual(view[0], "")
        self.assertEqual(view[2].get("value", view[2])["data"], [])
        self.assertEqual(view[12].get("value", view[12])["data"], [])

    def test_language_switch_translates_results_and_errors_and_isolates_sessions(self):
        client = Client(self.client.src, verbose=False)
        workspace, _ = client.predict(api_name="/demo")
        selected, _, _, _ = client.predict(workspace["value"], api_name="/select_workspace")
        dataset = selected["value"]
        view = client.predict(dataset, api_name="/load_dataset")
        rules = view[0]
        preview = client.predict(dataset, rules, api_name="/preview")
        # Only presentation fields are language-change inputs; unsaved JSON and CSV
        # data are never round-tripped or rewritten by the language selector.
        for code, valid_label, preview_label, error in (
            ("en", "Valid rows", "Preview calculated", "valid JSON"),
            ("es", "Filas válidas", "Vista previa calculada", "JSON válido"),
            ("de", "Gültige Zeilen", "Vorschau aus dem Original", "gültiges JSON"),
        ):
            changed = client.predict(code, preview[5], view[4], preview[4], preview[2],
                                     view[3]["value"], view[5]["value"],
                                     preview[3]["value"], api_name="/change_language")
            self.assertTrue(any(isinstance(item, str) and preview_label in item for item in changed))
            result = client.predict(dataset, rules, api_name="/preview")
            self.assertIn(valid_label, result[2])
            self.assertIn(preview_label, result[5])
            self.assertEqual(result[1]["value"]["data"], preview[1]["value"]["data"])
            self.assertEqual(client.predict(dataset, api_name="/load_dataset")[0], rules)
            with self.assertRaisesRegex(Exception, error):
                client.predict(dataset, "{broken", api_name="/preview")
        # A fresh browser session still starts in Spanish.
        other = Client(self.client.src, verbose=False)
        another_workspace, _ = other.predict(api_name="/demo")
        another_dataset, _, _, _ = other.predict(another_workspace["value"], api_name="/select_workspace")
        another_id = another_dataset["value"]
        another_rules = other.predict(another_id, api_name="/load_dataset")[0]
        self.assertIn("Filas válidas", other.predict(another_id, another_rules, api_name="/preview")[2])
