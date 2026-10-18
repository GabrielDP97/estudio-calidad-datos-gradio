import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import sqlite3

from quality_studio.engine import DataError, digest
from quality_studio.store import Studio

ROOT = Path(__file__).resolve().parent.parent


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.studio = Studio(self.directory.name)
        self.workspace = self.studio.create_workspace("Clientes")
        self.raw = (ROOT / "examples/clientes.csv").read_bytes()
        self.dataset = self.studio.add_dataset(self.workspace, self.raw, "clientes.csv")
        self.rules = json.loads((ROOT / "examples/clientes.reglas.json").read_text(encoding="utf-8"))

    def test_preview_does_not_create_runs_or_change_input(self):
        _, result = self.studio.preview(self.dataset, self.rules)
        self.assertEqual(len(result["clean"]), 3)
        self.assertEqual(self.studio.history(self.workspace), [])
        self.assertEqual(self.studio.input_path(self.dataset).read_bytes(), self.raw)

    def test_full_execution_reports_downloads_hashes_and_reopens(self):
        run_id, result, report, artifacts = self.studio.execute(self.dataset, self.rules)
        self.assertEqual(len(artifacts), 5)
        self.assertTrue(all(Path(path).is_file() for path in artifacts))
        self.assertEqual(digest(Path(artifacts[0]).read_bytes()), report["output_sha256"])
        reopened = Studio(self.directory.name)
        self.assertEqual(reopened.history(self.workspace)[0]["id"], run_id)
        self.assertEqual(reopened.load(self.dataset).sha256, digest(self.raw))
        self.assertEqual(json.loads(Path(artifacts[3]).read_text(encoding="utf-8")), report)

    def test_repeated_runs_have_same_result_different_audit_ids(self):
        a = self.studio.execute(self.dataset, self.rules)
        b = self.studio.execute(self.dataset, self.rules)
        self.assertNotEqual(a[0], b[0])
        self.assertEqual(a[2]["output_sha256"], b[2]["output_sha256"])
        self.assertEqual(a[2]["rules_sha256"], b[2]["rules_sha256"])
        self.assertEqual(len(self.studio.history(self.workspace)), 2)

    def test_invalid_rules_preserve_history_and_original(self):
        self.studio.execute(self.dataset, self.rules)
        with self.assertRaises(DataError):
            self.studio.execute(self.dataset, '{"version":1,"exec":"anything"}')
        self.assertEqual(len(self.studio.history(self.workspace)), 1)
        self.assertEqual(self.studio.input_path(self.dataset).read_bytes(), self.raw)

    def test_multiple_csv_and_identical_upload_are_idempotent(self):
        self.assertEqual(self.studio.add_dataset(self.workspace, self.raw, "otra-copia.csv"), self.dataset)
        other = self.studio.add_dataset(self.workspace, b"sku,precio\nx,1\n", "productos.csv")
        self.assertNotEqual(other, self.dataset)
        self.assertEqual(len(self.studio.list_datasets(self.workspace)), 2)

    def test_workspace_isolation_and_path_traversal(self):
        other = self.studio.create_workspace("../Nombre visible")
        self.assertEqual(self.studio.list_datasets(other), [])
        self.assertEqual(self.studio.history(other), [])
        for name in ("../../bad.csv", "bad.txt", "a\\b.csv"):
            with self.assertRaises(DataError):
                self.studio.add_dataset(other, self.raw, name)
        with self.assertRaises(DataError):
            self.studio.load("../../etc/passwd")

    def test_restore_preserves_history_and_original(self):
        self.studio.execute(self.dataset, self.rules)
        self.studio.restore_rules(self.dataset)
        self.assertEqual(len(self.studio.history(self.workspace)), 1)
        self.assertEqual(self.studio.load(self.dataset).rows[0][1], " Ana Torres ")
        self.assertFalse(json.loads(self.studio.get_rules(self.dataset))["drop_duplicates"])

    def test_modified_original_is_detected(self):
        self.studio.input_path(self.dataset).write_bytes(b"a\nchanged\n")
        with self.assertRaisesRegex(DataError, "ha cambiado"):
            self.studio.load(self.dataset)

    def test_invalid_csv_does_not_change_dataset_list(self):
        with self.assertRaises(DataError):
            self.studio.add_dataset(self.workspace, b"a,a\nx,y\n", "bad.csv")
        self.assertEqual(len(self.studio.list_datasets(self.workspace)), 1)

    def test_failed_database_insert_cleans_new_artifacts(self):
        original_connection = self.studio.connection
        @contextmanager
        def failing_connection():
            with original_connection() as db:
                class Proxy:
                    def execute(self, sql, *args):
                        if sql.startswith("INSERT INTO runs"):
                            raise sqlite3.OperationalError("synthetic failure")
                        return db.execute(sql, *args)
                yield Proxy()
        with patch.object(self.studio, "connection", failing_connection), self.assertRaises(sqlite3.OperationalError):
            self.studio.execute(self.dataset, self.rules)
        self.assertEqual(self.studio.history(self.workspace), [])
        runs = Path(self.directory.name) / self.workspace / "runs"
        self.assertEqual(list(runs.iterdir()), [])
        self.assertEqual(self.studio.input_path(self.dataset).read_bytes(), self.raw)

    def test_missing_artifacts_are_reported(self):
        run_id, _, _, files = self.studio.execute(self.dataset, self.rules)
        Path(files[0]).unlink()
        with self.assertRaises(DataError):
            self.studio.artifacts(run_id)
