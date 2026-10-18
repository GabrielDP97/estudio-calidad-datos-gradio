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
