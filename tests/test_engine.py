import copy
import csv
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from quality_studio.engine import (DataError, canonical, csv_bytes, digest, profile,
                                   read_csv, run_pipeline, suggested_rules, validate_rules, valid_type)

ROOT = Path(__file__).resolve().parent.parent


class CsvTests(unittest.TestCase):
    def test_utf8_bom_semicolon_quotes_and_leading_zeroes(self):
        dataset = read_csv('\ufeffid;nombre;nota\n001;Inés;"hola; mundo"\n002;Omar;"dos\nlíneas"\n'.encode())
        self.assertEqual(dataset.delimiter, ";")
        self.assertEqual(dataset.rows[0], ["001", "Inés", "hola; mundo"])
        self.assertEqual(dataset.rows[1][2], "dos\nlíneas")

    def test_explicit_windows_encoding(self):
        raw = "nombre,ciudad\nInés,Málaga\n".encode("cp1252")
        with self.assertRaises(DataError):
            read_csv(raw)
        self.assertEqual(read_csv(raw, encoding="cp1252").rows[0][1], "Málaga")

    def test_rejects_empty_duplicate_headers_and_invalid_records(self):
        for raw in (b"", b"a,a\n1,2", b"a,\n1,2", b"a,b\n1,2,3", b'a,b\n"unterminated,2', b"a,b\n", b"a\x00\n1"):
            with self.subTest(raw=raw), self.assertRaises(DataError):
                read_csv(raw)

    def test_resource_limits(self):
        for constant, limit, raw in (("MAX_BYTES", 3, b"a\nhello"), ("MAX_ROWS", 1, b"a\n1\n2"),
                                     ("MAX_CELLS", 1, b"a,b\n1,2"), ("MAX_COLUMNS", 1, b"a,b\n1,2")):
            with self.subTest(constant=constant), patch("quality_studio.engine." + constant, limit), self.assertRaises(DataError):
                read_csv(raw)

    def test_profile_keeps_missing_and_duplicate_counts(self):
        data = read_csv(b"id,email\n001,a@example.com\n001,a@example.com\n002,NULL\n")
        result = profile(data)
        self.assertEqual(result["duplicate_rows"], 1)
        self.assertEqual(result["columns"][1]["missing"], 1)
        self.assertEqual(result["columns"][1]["type_suggestion"], "email")


class RulesTests(unittest.TestCase):
    def test_schema_rejects_unknown_options_columns_and_invalid_json(self):
        for value in ("bad", "[]", '{"version":2}', {"version": 1, "exec": "anything"},
                      {"version": 1, "columns": {"missing": {}}}, {"version": 1, "drop_duplicates": "yes"}):
            with self.subTest(value=value), self.assertRaises(DataError):
                validate_rules(value, ["a"])

    def test_invalid_column_rules_are_rejected(self):
        for spec in ({"type": []}, {"date_format": {}}, {"type": "code"}, {"lowercase": True, "uppercase": True}, {"required": "yes"},
                     {"fill": 4}, {"replace": {"x": 7}}, {"type": "text", "min": 2},
                     {"type": "integer", "min": 4, "max": 1}, {"type": "decimal", "min": float("nan")},
                     {"type": "date", "date_format": "%c"}):
            with self.subTest(spec=spec), self.assertRaises(DataError):
                validate_rules({"version": 1, "columns": {"a": spec}}, ["a"])

    def test_composite_unique_and_duplicate_subsets_need_existing_columns(self):
        for extra in ({"unique": ["a"]}, {"unique": [["bad"]]}, {"unique": [["a", "a"]]},
                      {"duplicate_subset": ["bad"]}, {"duplicate_subset": ["a", "a"]}):
            with self.subTest(extra=extra), self.assertRaises(DataError):
                validate_rules({"version": 1, **extra}, ["a"])

    def test_rule_size_and_missing_tokens_are_bounded(self):
        with patch("quality_studio.engine.MAX_RULE_BYTES", 10), self.assertRaises(DataError):
            validate_rules('{"version":1}', ["a"])
        with self.assertRaises(DataError):
            validate_rules({"version": 1, "missing_values": [None]}, ["a"])

    def test_strict_dates_emails_numbers_and_booleans(self):
        for value, kind in (("2026-02-31", "date"), ("2026-1-01", "date"), ("a@b", "email"),
                            ("NaN", "decimal"), ("Infinity", "decimal"), ("2.4", "integer"), ("yes", "boolean")):
            self.assertFalse(valid_type(value, kind), (value, kind))
        self.assertTrue(valid_type("2024-02-29", "date"))
        self.assertTrue(valid_type("-3.2", "decimal"))


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.dataset = read_csv((ROOT / "examples/clientes.csv").read_bytes())
        self.rules = json.loads((ROOT / "examples/clientes.reglas.json").read_text(encoding="utf-8"))

    def test_full_example_preserves_original_and_splits_all_rows(self):
        original, rules = copy.deepcopy(self.dataset.rows), copy.deepcopy(self.rules)
        result = run_pipeline(self.dataset, self.rules)
        self.assertEqual(self.dataset.rows, original)
        self.assertEqual(self.rules, rules)
        self.assertEqual(result["summary"]["clean_rows"], 3)
        self.assertEqual(result["summary"]["rejected_rows"], 5)
        self.assertEqual(result["clean"][0][2], "ana@ejemplo.es")
        self.assertEqual(result["clean"][1][-1], "Sin indicar")
        self.assertTrue(any(issue["column"] == "fecha_alta" for issue in result["issues"]))

    def test_same_input_and_rules_produce_identical_bytes_and_hashes(self):
        a = run_pipeline(self.dataset, self.rules)
        b = run_pipeline(self.dataset, json.dumps(self.rules, sort_keys=True))
        self.assertEqual(a, b)
        self.assertEqual(digest(csv_bytes(self.dataset.columns, a["clean"])), digest(csv_bytes(self.dataset.columns, b["clean"])))
        self.assertEqual(canonical(a["rules"]), canonical(b["rules"]))

    def test_transformation_order_and_missing_fill(self):
        dataset = read_csv(b"value\n  NULL  \nABC\n")
        rules = {"version": 1, "columns": {"value": {"trim": True, "fill": "Desconocido", "replace": {"ABC": "Nuevo"}, "lowercase": True}}}
        result = run_pipeline(dataset, rules)
        self.assertEqual(result["clean"], [["desconocido"], ["nuevo"]])
        self.assertEqual(result["stages"]["Recortar espacios"], 1)

    def test_composite_uniqueness_after_normalization(self):
        data = read_csv(b"a,b\nx,1\nx,2\nx,1\n")
        result = run_pipeline(data, {"version": 1, "unique": [["a", "b"]]})
        self.assertEqual(len(result["clean"]), 2)
        self.assertEqual(result["rejected"][0][0], "4")

    def test_full_row_duplicates_and_subset_duplicates_differ(self):
        data = read_csv(b"a,b\nx,1\nx,2\nx,1\n")
        a = run_pipeline(data, {"version": 1, "drop_duplicates": True})
        b = run_pipeline(data, {"version": 1, "drop_duplicates": True, "duplicate_subset": ["a"]})
        self.assertEqual(len(a["clean"]), 2)
        self.assertEqual(len(b["clean"]), 1)

    def test_no_clean_rows_still_exports_headers(self):
        data = read_csv(b"email\nbad\n")
        result = run_pipeline(data, {"version": 1, "columns": {"email": {"type": "email"}}})
        self.assertEqual(result["after"]["rows"], 0)
        self.assertEqual(csv_bytes(data.columns, result["clean"]).decode("utf-8-sig"), "email\n")

    def test_csv_export_escapes_spreadsheet_formulas_but_keeps_negative_numbers(self):
        raw = csv_bytes(["v"], [["=1+1"], ["  @SUM(A1)"], ["-2.5"], ["001"], ["+cmd"], ["-cmd"]])
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
        self.assertEqual(rows[1][0], "'=1+1")
        self.assertEqual(rows[2][0], "'  @SUM(A1)")
        self.assertEqual(rows[3][0], "-2.5")
        self.assertEqual(rows[4][0], "001")

    def test_large_synthetic_input_is_complete_not_preview_truncated(self):
        data = read_csv(("id,email\n" + "".join(f"{i},user{i}@example.com\n" for i in range(5000))).encode())
        result = run_pipeline(data, suggested_rules(data))
        self.assertEqual(len(result["clean"]), 5000)
        self.assertEqual(len(result["after"]["columns"]), 2)


class DiagnosticLimitTests(unittest.TestCase):
    def test_too_many_issues_are_rejected_without_truncating_a_success(self):
        data = read_csv(b"email\nbad\nbad\n")
        with patch("quality_studio.engine.MAX_ISSUES", 1), self.assertRaises(DataError):
            run_pipeline(data, {"version": 1, "columns": {"email": {"type": "email"}}})


class MissingValueTests(unittest.TestCase):
    def test_case_conversion_preserves_missing_tokens(self):
        data = read_csv(b"email\nNULL\nA@EXAMPLE.COM\n")
        result = run_pipeline(data, {"version": 1, "columns": {"email": {"type": "email", "required": True, "lowercase": True}}})
        self.assertEqual(result["rows"][0][0], "NULL")
        self.assertEqual(result["issues"][0]["message"], "Valor obligatorio ausente")
        self.assertEqual(result["clean"], [["a@example.com"]])


class LargerCsvTests(unittest.TestCase):
    def test_accepts_csv_above_previous_size_and_row_limits_without_truncation(self):
        payload = "x" * 200
        raw = ("id,contenido\n" + "".join(f"{i:06d},{payload}\n" for i in range(110_000))).encode()
        self.assertGreater(len(raw), 20 * 1024 * 1024)
        data = read_csv(raw)
        self.assertEqual(len(data.rows), 110_000)
        self.assertEqual(data.rows[-1][0], "109999")

    def test_accepts_more_than_previous_cell_limit_and_enforces_boundary(self):
        header = ",".join(f"c{i}" for i in range(21)) + "\n"
        raw = (header + (",".join(["1"] * 21) + "\n") * 100_001).encode()
        self.assertEqual(len(read_csv(raw).rows), 100_001)
        # Un límite reducido comprueba la frontera real sin crear millones de celdas en CI.
        with patch("quality_studio.engine.MAX_CELLS", 4):
            self.assertEqual(len(read_csv(b"a,b\n1,2\n3,4\n").rows), 2)
            with self.assertRaises(DataError):
                read_csv(b"a,b\n1,2\n3,4\n5,6\n")
