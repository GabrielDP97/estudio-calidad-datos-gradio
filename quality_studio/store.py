"""Espacios de trabajo, originales inmutables y ejecuciones auditables en SQLite."""
import json
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .engine import (DataError, MAX_BYTES, canonical, csv_bytes, digest, profile,
                     read_csv, run_pipeline, suggested_rules, validate_rules)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class Studio:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / "studio.sqlite3"
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS workspaces(
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS datasets(
                    id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
                    name TEXT NOT NULL, sha256 TEXT NOT NULL, delimiter TEXT NOT NULL,
                    encoding TEXT NOT NULL, rules TEXT NOT NULL, created_at TEXT NOT NULL,
                    UNIQUE(workspace_id, sha256));
                CREATE TABLE IF NOT EXISTS runs(
                    id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES datasets(id),
                    created_at TEXT NOT NULL, input_hash TEXT NOT NULL, rules_hash TEXT NOT NULL,
                    output_hash TEXT NOT NULL, summary TEXT NOT NULL);
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.database, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def list_workspaces(self):
        with self.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM workspaces ORDER BY created_at DESC")]

    def create_workspace(self, name):
        if not isinstance(name, str) or not name.strip() or len(name) > 80 or any(ord(c) < 32 for c in name):
            raise DataError("Pon un nombre de proyecto de entre 1 y 80 caracteres.")
        token = uuid.uuid4().hex
        with self.connection() as db:
            db.execute("INSERT INTO workspaces VALUES(?,?,?)", (token, name.strip(), timestamp()))
        return token

    def workspace(self, token):
        with self.connection() as db:
            row = db.execute("SELECT * FROM workspaces WHERE id=?", (token,)).fetchone()
        if not row:
            raise DataError("Selecciona un proyecto existente.")
        return dict(row)

    def list_datasets(self, workspace_id):
        if not workspace_id:
            return []
        self.workspace(workspace_id)
        with self.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM datasets WHERE workspace_id=? ORDER BY created_at", (workspace_id,))]

    def info(self, dataset_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
        if not row:
            raise DataError("Selecciona un CSV del proyecto.")
        return dict(row)

    def input_path(self, dataset_id):
        info = self.info(dataset_id)
        return self.root / info["workspace_id"] / "inputs" / f"{info['id']}.csv"

    def load(self, dataset_id):
        info = self.info(dataset_id)
        path = self.input_path(dataset_id)
        if not path.is_file():
            raise DataError("Falta la copia original de este CSV.")
        if path.stat().st_size > MAX_BYTES:
            raise DataError(f"La copia original supera {MAX_BYTES // (1024 * 1024)} MiB. Carga un CSV dentro del límite.")
        raw = path.read_bytes()
        if digest(raw) != info["sha256"]:
            raise DataError("La copia original ha cambiado fuera de la aplicación. Carga el archivo de nuevo como otra versión.")
        return read_csv(raw, info["name"], info["delimiter"], info["encoding"])

    def add_dataset(self, workspace_id, raw, name, delimiter="auto", encoding="utf-8-sig"):
        self.workspace(workspace_id)
        if not isinstance(name, str) or not name.lower().endswith(".csv") or len(name) > 180 or any(c in name for c in "/\\") or any(ord(c) < 32 for c in name):
            raise DataError("Usa un nombre de archivo CSV sin rutas, de hasta 180 caracteres.")
        dataset = read_csv(raw, name, delimiter, encoding)
        with self.connection() as db:
            old = db.execute("SELECT id FROM datasets WHERE workspace_id=? AND sha256=?", (workspace_id, dataset.sha256)).fetchone()
            if old:
                return old["id"]
            count = db.execute("SELECT COUNT(*) FROM datasets WHERE workspace_id=?", (workspace_id,)).fetchone()[0]
            if count >= 10:
                raise DataError("Cada proyecto admite hasta 10 CSV distintos. Crea otro proyecto.")
            token = uuid.uuid4().hex
            directory = self.root / workspace_id / "inputs"
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f"{token}.csv"
            path.write_bytes(raw)
            try:
                db.execute("INSERT INTO datasets VALUES(?,?,?,?,?,?,?,?)", (token, workspace_id, name,
                    dataset.sha256, dataset.delimiter, dataset.encoding, canonical(suggested_rules(dataset)), timestamp()))
            except Exception:
                path.unlink(missing_ok=True)
                raise
        return token

    def get_rules(self, dataset_id):
        return self.info(dataset_id)["rules"]

    def save_rules(self, dataset_id, text):
        dataset = self.load(dataset_id)
        rules = validate_rules(text, dataset.columns)
        with self.connection() as db:
            db.execute("UPDATE datasets SET rules=? WHERE id=?", (canonical(rules), dataset_id))
        return rules

    def preview(self, dataset_id, text):
        dataset = self.load(dataset_id)
        return dataset, run_pipeline(dataset, text)

    def execute(self, dataset_id, text):
        dataset, result = self.preview(dataset_id, text)
        token, created = uuid.uuid4().hex, timestamp()
        info = self.info(dataset_id)
        runs = self.root / info["workspace_id"] / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        destination = runs / token
        clean = csv_bytes(dataset.columns, result["clean"])
        rules_hash = digest(canonical(result["rules"]).encode("utf-8"))
        report = {"version": 1, "engine_version": __version__, "run_id": token, "created_at": created,
                  "dataset": dataset.name, "input_sha256": dataset.sha256, "rules_sha256": rules_hash,
                  "output_sha256": digest(clean), "summary": result["summary"], "stages": result["stages"],
                  "profile_before": result["before"], "profile_after": result["after"],
                  "rules": result["rules"], "issues_before": result["before_issues"], "issues_after": result["issues"],
                  "notes": ["Los números de fila identifican registros CSV (cabecera = 1), no líneas físicas.",
                            "El archivo limpio excluye las filas con errores y los duplicados descartados.",
                            "Los CSV exportados protegen los textos que podrían interpretarse como fórmulas añadiendo un apóstrofo.",
                            "Los tipos sugeridos son heurísticos; el usuario debe revisar el contrato."]}
        with tempfile.TemporaryDirectory(prefix="staging-", dir=runs) as folder:
            staging = Path(folder)
            (staging / "limpio.csv").write_bytes(clean)
            (staging / "rechazadas.csv").write_bytes(csv_bytes(["__fila_origen", *dataset.columns], result["rejected"]))
            issue_columns = ["row", "column", "value", "message"]
            (staging / "incidencias.csv").write_bytes(csv_bytes(issue_columns,
                [[item[key] for key in issue_columns] for item in result["issues"]]))
            (staging / "informe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            (staging / "reglas.json").write_text(json.dumps(result["rules"], ensure_ascii=False, indent=2), encoding="utf-8")
            # Solo publicar archivos terminados; el historial se confirma después.
            staging.rename(destination)
            try:
                with self.connection() as db:
                    db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?)", (token, dataset_id, created, dataset.sha256,
                        rules_hash, digest(clean), canonical(result["summary"])))
                    db.execute("UPDATE datasets SET rules=? WHERE id=?", (canonical(result["rules"]), dataset_id))
            except Exception:
                # Directorio generado por nosotros y contenido en este proyecto, nunca una ruta del usuario.
                for file in destination.iterdir():
                    file.unlink()
                destination.rmdir()
                raise
        return token, result, report, self.artifacts(token)

    def history(self, workspace_id):
        if not workspace_id:
            return []
        self.workspace(workspace_id)
        with self.connection() as db:
            return [dict(row) for row in db.execute("""SELECT runs.*, datasets.name FROM runs JOIN datasets
                ON runs.dataset_id=datasets.id WHERE datasets.workspace_id=? ORDER BY runs.created_at DESC LIMIT 100""", (workspace_id,))]

    def run_info(self, run_id):
        with self.connection() as db:
            row = db.execute("SELECT runs.*, datasets.workspace_id FROM runs JOIN datasets ON runs.dataset_id=datasets.id WHERE runs.id=?", (run_id,)).fetchone()
        if not row:
            raise DataError("La ejecución no existe.")
        return dict(row)

    def artifacts(self, run_id):
        info = self.run_info(run_id)
        directory = self.root / info["workspace_id"] / "runs" / info["id"]
        paths = [directory / name for name in ("limpio.csv", "rechazadas.csv", "incidencias.csv", "informe.json", "reglas.json")]
        if not all(path.is_file() for path in paths):
            raise DataError("Faltan archivos de esta ejecución; no se ha modificado el original.")
        return [str(path) for path in paths]

    def restore_rules(self, dataset_id):
        dataset = self.load(dataset_id)
        return self.save_rules(dataset_id, suggested_rules(dataset))
