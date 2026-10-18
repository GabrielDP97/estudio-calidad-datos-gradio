"""Lectura CSV, contratos declarativos y transformaciones deterministas."""
import csv
import hashlib
import io
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

MAX_BYTES = 100 * 1024 * 1024
MAX_ROWS = 500_000
MAX_COLUMNS = 100
MAX_CELLS = 5_000_000
MAX_RULE_BYTES = 100_000
MAX_ISSUES = 20_000
MISSING = ["", "NULL", "N/A"]
TYPES = {"text", "integer", "decimal", "email", "date", "boolean"}
FORMATS = {"%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"}
csv.field_size_limit(1_000_000)


class DataError(ValueError):
    """Entrada inválida; el original no se modifica."""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass
class Dataset:
    name: str
    columns: list
    rows: list
    sha256: str
    delimiter: str
    encoding: str


def read_csv(raw, name="datos.csv", delimiter="auto", encoding="utf-8-sig"):
    if not raw or len(raw) > MAX_BYTES:
        raise DataError(f"El CSV está vacío o supera {MAX_BYTES // (1024 * 1024)} MiB.")
    if encoding not in {"utf-8-sig", "cp1252"}:
        raise DataError("Codificación no admitida.")
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError as exc:
        raise DataError("No se pudo leer la codificación. Prueba Windows-1252 si el CSV no es UTF-8.") from exc
    if "\x00" in text:
        raise DataError("El CSV contiene datos binarios.")
    if delimiter == "auto":
        try:
            delimiter = csv.Sniffer().sniff(text[:65536], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    if delimiter not in {",", ";", "\t", "|"}:
        raise DataError("Separador no admitido.")
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
        columns = [c.strip() for c in next(reader)]
        if not 1 <= len(columns) <= MAX_COLUMNS or any(not c or len(c) > 120 for c in columns):
            raise DataError("Usa entre 1 y 100 columnas con nombres no vacíos de hasta 120 caracteres.")
        if len(set(columns)) != len(columns):
            raise DataError("Hay nombres de columna duplicados.")
        rows = []
        for row in reader:
            if not row:
                continue
            if len(row) != len(columns):
                raise DataError(f"El registro {len(rows) + 2} tiene un número de columnas incorrecto.")
            rows.append(row)
            if len(rows) > MAX_ROWS or len(rows) * len(columns) > MAX_CELLS:
                raise DataError(f"El CSV supera {MAX_ROWS:,} filas o {MAX_CELLS:,} celdas.".replace(",", " "))
        if not rows:
            raise DataError("El CSV solo contiene la cabecera; añade al menos una fila.")
    except (csv.Error, StopIteration) as exc:
        raise DataError("CSV incompleto, comillas incorrectas o campo demasiado grande.") from exc
    return Dataset(name, columns, rows, digest(raw), delimiter, encoding)


def numeric(value):
    try:
        number = Decimal(value)
        return number if number.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def valid_type(value, kind, date_format="%Y-%m-%d"):
    if kind == "integer":
        return bool(re.fullmatch(r"[+-]?\d+", value))
    if kind == "decimal":
        return numeric(value) is not None
    if kind == "email":
        return bool(re.fullmatch(r"[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+", value))
    if kind == "date":
        try:
            return datetime.strptime(value, date_format).strftime(date_format) == value
        except ValueError:
            return False
    if kind == "boolean":
        return value.casefold() in {"true", "false", "1", "0", "sí", "si", "no"}
    return True


def profile(dataset, rows=None, missing=None):
    rows = dataset.rows if rows is None else rows
    missing = set(MISSING if missing is None else missing)
    result = []
    for index, name in enumerate(dataset.columns):
        values = [row[index] for row in rows]
        present = [value for value in values if value not in missing]
        inferred = "text"
        if present:
            for kind in ("integer", "decimal", "date", "email", "boolean"):
                if sum(valid_type(v.strip(), kind) for v in present) / len(present) >= .8:
                    inferred = kind
                    break
        result.append({"column": name, "type_suggestion": inferred, "rows": len(rows),
                       "missing": len(values) - len(present), "distinct": len(set(present)),
                       "examples": list(dict.fromkeys(present))[:3]})
    return {"rows": len(rows), "columns": result,
            "duplicate_rows": len(rows) - len({tuple(row) for row in rows})}


def suggested_rules(dataset):
    return {"version": 1, "columns": {col["column"]: {"type": col["type_suggestion"], "trim": True}
            for col in profile(dataset)["columns"]}, "unique": [], "drop_duplicates": False,
            "duplicate_subset": [], "missing_values": MISSING.copy()}


def validate_rules(value, columns):
    if isinstance(value, str):
        if len(value.encode("utf-8")) > MAX_RULE_BYTES:
            raise DataError("Las reglas superan 100 KB.")
        try:
            value = json.loads(value)
        except (ValueError, RecursionError) as exc:
            raise DataError("Las reglas no contienen un JSON válido.") from exc
    if not isinstance(value, dict) or value.get("version") != 1 or isinstance(value.get("version"), bool):
        raise DataError("Las reglas deben ser un objeto JSON con version: 1.")
    allowed = {"version", "columns", "unique", "drop_duplicates", "duplicate_subset", "missing_values"}
    if set(value) - allowed:
        raise DataError("Hay opciones de reglas desconocidas.")
    specs = value.get("columns", {})
    if not isinstance(specs, dict) or set(specs) - set(columns):
        raise DataError("Las reglas mencionan columnas que no existen.")
    for name, spec in specs.items():
        if not isinstance(spec, dict) or set(spec) - {"type", "required", "trim", "lowercase", "uppercase", "fill", "replace", "min", "max", "date_format"}:
            raise DataError(f"Regla no válida en {name}.")
        if not isinstance(spec.get("type", "text"), str) or not isinstance(spec.get("date_format", "%Y-%m-%d"), str) or spec.get("type", "text") not in TYPES or spec.get("date_format", "%Y-%m-%d") not in FORMATS:
            raise DataError(f"Tipo o formato de fecha no admitido en {name}.")
        for flag in ("required", "trim", "lowercase", "uppercase"):
            if flag in spec and not isinstance(spec[flag], bool):
                raise DataError(f"{flag} debe ser verdadero o falso en {name}.")
        if spec.get("lowercase") and spec.get("uppercase"):
            raise DataError(f"No se pueden aplicar mayúsculas y minúsculas a la vez en {name}.")
        if "fill" in spec and (not isinstance(spec["fill"], str) or len(spec["fill"]) > 10000):
            raise DataError("El relleno debe ser un texto de hasta 10 000 caracteres.")
        replacements = spec.get("replace", {})
        if not isinstance(replacements, dict) or len(replacements) > 100 or any(not isinstance(k, str) or not isinstance(v, str) or len(k) + len(v) > 20000 for k, v in replacements.items()):
            raise DataError("Las sustituciones deben ser un objeto de textos, con un máximo de 100 entradas.")
        for bound in ("min", "max"):
            if bound in spec and (isinstance(spec[bound], bool) or not isinstance(spec[bound], (int, float)) or (isinstance(spec[bound], float) and not math.isfinite(spec[bound]))):
                raise DataError("Los límites numéricos deben ser números finitos.")
        if any(b in spec for b in ("min", "max")) and spec.get("type") not in {"integer", "decimal"}:
            raise DataError("Los límites mínimo/máximo requieren un tipo numérico.")
        if spec.get("min", -math.inf) > spec.get("max", math.inf):
            raise DataError("El mínimo no puede superar al máximo.")
    unique = value.get("unique", [])
    if not isinstance(unique, list) or len(unique) > MAX_COLUMNS:
        raise DataError("unique debe ser una lista de claves.")
    for key in unique:
        if not isinstance(key, list) or not key or any(not isinstance(c, str) or c not in columns for c in key) or len(key) != len(set(key)):
            raise DataError("Cada clave única debe contener columnas existentes, sin repetir.")
    subset = value.get("duplicate_subset", [])
    if not isinstance(subset, list) or any(not isinstance(c, str) or c not in columns for c in subset) or len(subset) != len(set(subset)):
        raise DataError("La clave de duplicados debe contener columnas existentes, sin repetir.")
    if not isinstance(value.get("drop_duplicates", False), bool):
        raise DataError("drop_duplicates debe ser verdadero o falso.")
    missing = value.get("missing_values", MISSING)
    if not isinstance(missing, list) or len(missing) > 100 or any(not isinstance(v, str) or len(v) > 1000 for v in missing):
        raise DataError("missing_values debe ser una lista de textos (máximo 100).")
    result = {"version": 1, "columns": specs, "unique": unique,
              "drop_duplicates": value.get("drop_duplicates", False), "duplicate_subset": subset,
              "missing_values": missing}
    if len(canonical(result).encode("utf-8")) > MAX_RULE_BYTES:
        raise DataError("Las reglas superan 100 KB.")
    return json.loads(canonical(result))


def audit(dataset, rows, rules, skip=None):
    issues = []
    skip = set() if skip is None else skip
    missing = set(rules["missing_values"])
    for offset, row in enumerate(rows):
        if offset in skip:
            continue
        for index, column in enumerate(dataset.columns):
            spec, value = rules["columns"].get(column, {}), row[index]
            problem = None
            if value in missing:
                if spec.get("required"):
                    problem = "Valor obligatorio ausente"
            elif not valid_type(value, spec.get("type", "text"), spec.get("date_format", "%Y-%m-%d")):
                problem = "Formato incorrecto: " + spec.get("type", "text")
            elif any(b in spec for b in ("min", "max")):
                number = numeric(value)
                if number is None or ("min" in spec and number < Decimal(str(spec["min"]))) or ("max" in spec and number > Decimal(str(spec["max"]))):
                    problem = "Valor fuera del rango permitido"
            if problem:
                issues.append({"row": offset + 2, "column": column, "value": value, "message": problem})
                if len(issues) > MAX_ISSUES:
                    raise DataError("Hay más de 20 000 incidencias. Divide el CSV o revisa las reglas.")
    for key in rules["unique"]:
        indices, seen = [dataset.columns.index(c) for c in key], set()
        for offset, row in enumerate(rows):
            if offset in skip:
                continue
            value = tuple(row[i] for i in indices)
            if any(v in missing for v in value):
                continue
            if value in seen:
                issues.append({"row": offset + 2, "column": "+".join(key), "value": " | ".join(value), "message": "Clave única duplicada (se conserva la primera aparición)"})
            seen.add(value)
            if len(issues) > MAX_ISSUES:
                raise DataError("Hay más de 20 000 incidencias. Divide el CSV o revisa las reglas.")
    return issues


def run_pipeline(dataset, rule_value):
    rules = validate_rules(rule_value, dataset.columns)
    before = audit(dataset, dataset.rows, rules)
    rows = [row.copy() for row in dataset.rows]
    missing = set(rules["missing_values"])
    stages = Counter()
    for row in rows:
        for index, column in enumerate(dataset.columns):
            spec, value = rules["columns"].get(column, {}), row[index]
            operations = []
            if spec.get("trim"):
                operations.append(("Recortar espacios", lambda v: v.strip()))
            if "fill" in spec:
                operations.append(("Rellenar ausentes", lambda v, s=spec: s["fill"] if v in missing else v))
            if spec.get("replace"):
                operations.append(("Sustituir valores", lambda v, s=spec: s["replace"].get(v, v)))
            if spec.get("lowercase"):
                operations.append(("Minúsculas", lambda v: v if v in missing else v.lower()))
            if spec.get("uppercase"):
                operations.append(("Mayúsculas", lambda v: v if v in missing else v.upper()))
            for label, operation in operations:
                updated = operation(value)
                stages[label] += updated != value
                value = updated
            row[index] = value
    dropped = set()
    if rules["drop_duplicates"]:
        subset = rules["duplicate_subset"] or dataset.columns
        indices, seen = [dataset.columns.index(c) for c in subset], set()
        for offset, row in enumerate(rows):
            key = tuple(row[i] for i in indices)
            if key in seen:
                dropped.add(offset)
            seen.add(key)
        stages["Excluir duplicados"] = len(dropped)
    issues = audit(dataset, rows, rules, skip=dropped)
    issues.extend({"row": i + 2, "column": "*", "value": "", "message": "Duplicado excluido por las reglas"} for i in sorted(dropped))
    if len(issues) > MAX_ISSUES:
        raise DataError("Hay más de 20 000 incidencias. Divide el CSV o revisa las reglas.")
    issues.sort(key=lambda item: (item["row"], item["column"], item["message"]))
    rejected_ids = {issue["row"] - 2 for issue in issues}
    clean = [row for index, row in enumerate(rows) if index not in rejected_ids]
    rejected = [[str(index + 2), *row] for index, row in enumerate(rows) if index in rejected_ids]
    changed = sum(a != b for original, changed_row in zip(dataset.rows, rows) for a, b in zip(original, changed_row))
    return {"rules": rules, "rows": rows, "clean": clean, "rejected": rejected,
            "issues": issues, "before_issues": before, "before": profile(dataset, missing=missing),
            "after": profile(dataset, clean, missing), "stages": dict(stages),
            "summary": {"input_rows": len(rows), "clean_rows": len(clean), "rejected_rows": len(rejected),
                        "changed_cells": changed, "issues_before": len(before), "issues_after": len(issues)}}


def csv_bytes(columns, rows):
    """Exportaciones deterministas con protección frente a fórmulas de hojas de cálculo."""
    def safe(value):
        value = str(value)
        inspected = value.lstrip()
        if inspected.startswith(("=", "+", "@")) or (inspected.startswith("-") and numeric(inspected) is None):
            return "'" + value
        return value
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow([safe(c) for c in columns])
    writer.writerows([safe(c) for c in row] for row in rows)
    return stream.getvalue().encode("utf-8-sig")
