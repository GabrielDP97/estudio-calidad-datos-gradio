"""Interfaz Gradio: el dominio y la persistencia están en módulos independientes."""
import functools
import json
import os
import sqlite3
import uuid
from pathlib import Path

os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
import gradio as gr

from .engine import DataError, MAX_BYTES, MAX_RULE_BYTES, audit, profile, validate_rules
from .store import Studio

ROOT = Path(__file__).resolve().parent.parent


def guarded(function):
    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except DataError as exc:
            raise gr.Error(str(exc)) from None
        except (OSError, sqlite3.Error):
            raise gr.Error("No se pudo leer o guardar el proyecto. Comprueba el espacio libre y los permisos; el original se conserva.") from None
    return wrapped


def pretty(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def frame(columns, rows):
    # No inferir números: conservar identificadores, ceros iniciales y valores originales.
    return gr.Dataframe(headers=columns, value=rows[:100], datatype="str", interactive=False, type="array")


def metrics(summary, preview=False):
    values = [("Filas de entrada", summary["input_rows"]), ("Filas válidas", summary["clean_rows"]),
              ("Filas excluidas", summary["rejected_rows"]), ("Celdas modificadas", summary["changed_cells"])]
    return '<div class="metrics">' + ''.join(f'<div><span>{label}</span><strong>{value:,}</strong></div>' for label, value in values) + '</div>'


def profile_rows(value):
    return [[c["column"], c["type_suggestion"], c["rows"], c["missing"], c["distinct"], " | ".join(c["examples"])] for c in value["columns"]]


def issue_rows(issues):
    return [[i["row"], i["column"], i["value"], i["message"]] for i in issues[:100]]


CSS = """
body,.gradio-container{background:#f7f8f4!important;font-family:Inter,Segoe UI,Arial,sans-serif!important}
.gradio-container{max-width:1360px!important;margin:auto!important;padding:30px!important}
.studio-hero{padding:18px 0 30px;border-bottom:1px solid #dbe2db;margin-bottom:24px}
.studio-hero .eyebrow{font-size:12px;color:#337365;letter-spacing:2px;font-weight:700}
.studio-hero h1{font-size:43px;letter-spacing:-1.8px;color:#183c35;font-weight:650;margin:12px 0}
.studio-hero p{font-size:15px;line-height:1.8;color:#60736b;max-width:750px}
.local-tag{float:right;border:1px solid #cddbd1;padding:8px 14px;border-radius:30px;color:#337365;font-size:12px}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:12px 0 22px}
.metrics>div{padding:18px;background:#ecf3ee;border:1px solid #d9e6dc;border-radius:12px}
.metrics span{font-size:11px;color:#667d70;display:block}.metrics strong{font-size:30px;color:#225948;display:block;margin-top:6px}
.studio-foot{font-size:12px;color:#60736b;padding-top:20px;line-height:1.8}
@media(max-width:700px){.gradio-container{padding:14px!important}.studio-hero h1{font-size:31px}.local-tag{float:none;display:inline-block;margin-bottom:10px}.metrics{grid-template-columns:repeat(2,1fr)}}
"""


def build_app(storage_root=None):
    studio = Studio(storage_root or ROOT / ".private" / "data")

    def workspace_choices():
        return [(w["name"], w["id"]) for w in studio.list_workspaces()]

    def datasets_update(workspace_id, selected=None):
        items = studio.list_datasets(workspace_id)
        choices = [(f"{item['name']} · {item['sha256'][:8]}", item["id"]) for item in items]
        return gr.Dropdown(choices=choices, value=selected or (items[0]["id"] if items else None))

    def history_updates(workspace_id, selected=None):
        history = studio.history(workspace_id)
        rows = []
        for run in history:
            summary = json.loads(run["summary"])
            rows.append([run["created_at"][:19].replace("T", " ") + " UTC", run["name"],
                         summary["clean_rows"], summary["rejected_rows"], run["output_hash"][:16], run["id"]])
        choices = [(f"{r['created_at'][:19]} · {r['name']} · {r['id'][:8]}", r["id"]) for r in history]
        return frame(["Fecha UTC", "CSV", "Válidas", "Excluidas", "SHA-256 salida (inicio)", "ID"], rows), gr.Dropdown(choices=choices, value=selected)

    @guarded
    def create_workspace(name):
        token = studio.create_workspace(name)
        return gr.Dropdown(choices=workspace_choices(), value=token), "Proyecto creado. Añade uno o varios CSV."

    @guarded
    def select_workspace(token):
        return datasets_update(token), *history_updates(token), "Selecciona un CSV para revisar su contrato y diagnóstico."

    @guarded
    def add_files(token, paths, separator, encoding):
        if not token:
            raise DataError("Crea o selecciona un proyecto antes de añadir archivos.")
        if not paths or len(paths) > 10:
            raise DataError("Selecciona entre 1 y 10 CSV.")
        added, errors, selected = 0, [], None
        for path in paths:
            try:
                source = Path(path)
                if source.stat().st_size > MAX_BYTES:
                    raise DataError("El archivo supera 20 MiB.")
                selected = studio.add_dataset(token, source.read_bytes(), source.name, separator, encoding)
                added += 1
            except DataError as exc:
                errors.append(f"{Path(path).name}: {exc}")
        return datasets_update(token, selected), f"{added} archivos incorporados o ya existentes." + ("\n" + "\n".join(errors) if errors else "")

    @guarded
    def demo():
        token = studio.create_workspace("Ejemplo · Clientes y productos")
        for name in ("clientes", "productos"):
            dataset_id = studio.add_dataset(token, (ROOT / "examples" / f"{name}.csv").read_bytes(), f"{name}.csv")
            studio.save_rules(dataset_id, (ROOT / "examples" / f"{name}.reglas.json").read_text(encoding="utf-8"))
        return gr.Dropdown(choices=workspace_choices(), value=token), "Ejemplo creado con dos CSV y contratos preparados. Abre Reglas y limpieza para previsualizarlo."

    @guarded
    def load_dataset(token):
        if not token:
            return ("", gr.Dropdown(choices=[], value=None), frame([], []), frame([], []),
                    "Selecciona un CSV para ver su diagnóstico.", frame([], []), None,
                    frame([], []), frame([], []), "", None, "")
        dataset = studio.load(token)
        rules = validate_rules(studio.get_rules(token), dataset.columns)
        issues = audit(dataset, dataset.rows, rules)
        stats = profile(dataset)
        diagnostics = (f"**{len(dataset.rows):,} filas · {len(dataset.columns)} columnas · "
                       f"{stats['duplicate_rows']} filas idénticas repetidas · {len(issues)} incidencias del contrato guardado.**\n\n"
                       "Los tipos sugeridos son orientativos. Las tablas muestran hasta 100 registros. "
                       f"Original SHA-256: `{dataset.sha256}`")
        return (pretty(rules), gr.Dropdown(choices=dataset.columns, value=dataset.columns[0]),
                frame(dataset.columns, dataset.rows),
                frame(["Columna", "Tipo sugerido", "Filas", "Ausentes", "Distintos", "Ejemplos"], profile_rows(stats)),
                diagnostics, frame(["Fila CSV", "Columna", "Valor", "Incidencia"], issue_rows(issues)),
                str(studio.input_path(token)), frame(dataset.columns, dataset.rows), frame(dataset.columns, []),
                "", None, "Original cargado. Edita las reglas y pulsa Vista previa; no se ha guardado una ejecución.")

    @guarded
    def apply_column(token, text, column, kind, required, trim, casing, fill_enabled, fill, minimum, maximum, date_format, unique, dedupe, subset):
        dataset = studio.load(token)
        rules = validate_rules(text, dataset.columns)
        if column not in dataset.columns:
            raise DataError("Selecciona una columna.")
        spec = {"type": kind, "required": required, "trim": trim,
                "lowercase": casing == "Minúsculas", "uppercase": casing == "Mayúsculas"}
        # Conservar sustituciones avanzadas cuando se edita con el formulario.
        if "replace" in rules["columns"].get(column, {}):
            spec["replace"] = rules["columns"][column]["replace"]
        if fill_enabled:
            spec["fill"] = fill
        if kind == "date":
            spec["date_format"] = date_format
        for key, value in (("min", minimum), ("max", maximum)):
            if str(value).strip():
                try:
                    spec[key] = float(value)
                except ValueError:
                    raise DataError("El mínimo y máximo deben ser números con punto decimal.") from None
        rules["columns"][column] = spec
        rules["unique"] = [key for key in rules["unique"] if key != [column]]
        if unique:
            rules["unique"].append([column])
        rules["drop_duplicates"], rules["duplicate_subset"] = dedupe, subset or []
        return pretty(validate_rules(rules, dataset.columns)), "Regla incorporada al JSON. Pulsa Vista previa para comprobar su efecto."

    @guarded
    def read_column(token, text, column):
        if not token or not column:
            return "text", False, True, "Sin cambio", False, "", "", "", "%Y-%m-%d", False, False, gr.Dropdown(choices=[], value=[])
        dataset = studio.load(token)
        rules = validate_rules(text, dataset.columns)
        spec = rules["columns"].get(column, {})
        return (spec.get("type", "text"), spec.get("required", False), spec.get("trim", False),
                "Minúsculas" if spec.get("lowercase") else "Mayúsculas" if spec.get("uppercase") else "Sin cambio",
                "fill" in spec, spec.get("fill", ""), str(spec.get("min", "")), str(spec.get("max", "")),
                spec.get("date_format", "%Y-%m-%d"), [column] in rules["unique"], rules["drop_duplicates"],
                gr.Dropdown(choices=dataset.columns, value=rules["duplicate_subset"]))

    def result_outputs(dataset, result):
        summary = result["summary"]
        explanation = (f"Incidencias antes: {summary['issues_before']} · Incidencias después: {summary['issues_after']}. "
                       "Las filas excluidas incluyen errores pendientes y duplicados descartados; las incidencias se cuentan por celda o restricción.\n\n"
                       "Etapas: " + ", ".join(f"{key}: {value}" for key, value in result["stages"].items()) + ".")
        return (frame(dataset.columns, dataset.rows), frame(dataset.columns, result["rows"]), metrics(summary),
                frame(["Fila CSV", "Columna", "Valor", "Incidencia"], issue_rows(result["issues"])), explanation)

    @guarded
    def preview(token, text):
        dataset, result = studio.preview(token, text)
        return (*result_outputs(dataset, result), "Vista previa calculada sobre el original. Todavía no se ha guardado ninguna ejecución.", gr.Tabs(selected="comparison"))

    @guarded
    def execute(workspace_id, token, text):
        if studio.info(token)["workspace_id"] != workspace_id:
            raise DataError("El CSV no pertenece al proyecto seleccionado.")
        run_id, result, report, artifacts = studio.execute(token, text)
        dataset = studio.load(token)
        return (*result_outputs(dataset, result), artifacts, *history_updates(workspace_id, run_id),
                pretty(report), f"Ejecución guardada: {run_id}. Salida SHA-256: {report['output_sha256']}", gr.Tabs(selected="comparison"))

    @guarded
    def save_rules(token, text):
        studio.save_rules(token, text)
        return "Contrato guardado para este CSV. El historial previo se conserva."

    @guarded
    def import_rules(token, path):
        dataset = studio.load(token)
        if not path or Path(path).stat().st_size > MAX_RULE_BYTES:
            raise DataError("Selecciona reglas JSON de hasta 100 KB.")
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            raise DataError("El JSON debe estar codificado en UTF-8.") from None
        return pretty(validate_rules(text, dataset.columns)), "Reglas importadas a la vista de edición; revisa y guarda cuando quieras."

    @guarded
    def export_rules(token, text):
        dataset = studio.load(token)
        rules = validate_rules(text, dataset.columns)
        directory = studio.root / "exports"
        directory.mkdir(exist_ok=True)
        path = directory / f"reglas-{uuid.uuid4().hex[:10]}.json"
        path.write_text(pretty(rules), encoding="utf-8")
        return str(path), "Reglas preparadas para descargar."

    @guarded
    def restore(token):
        studio.restore_rules(token)
        return load_dataset(token)

    @guarded
    def show_run(workspace_id, token):
        if not token:
            return None, ""
        if studio.run_info(token)["workspace_id"] != workspace_id:
            raise DataError("La ejecución no pertenece al proyecto seleccionado.")
        paths = studio.artifacts(token)
        return paths, Path(paths[3]).read_text(encoding="utf-8")

    with gr.Blocks(title="Dato · Estudio de calidad", analytics_enabled=False) as app:
        gr.HTML('<div class="studio-hero"><span class="local-tag">● Local · Sin servicios de pago</span><div class="eyebrow">DATO / ESTUDIO DE CALIDAD</div><h1>Datos que merecen confianza.</h1><p>Encuentra errores, prepara reglas y revisa cada cambio antes de guardar una copia limpia. Tus originales siempre se conservan.</p></div>')
        with gr.Row():
            with gr.Column(scale=1, min_width=270):
                gr.Markdown("### 01 / Tu espacio de trabajo")
                workspace = gr.Dropdown(choices=workspace_choices(), label="Proyecto", interactive=True)
                with gr.Accordion("Crear un proyecto", open=False):
                    project_name = gr.Textbox(label="Nombre del proyecto", placeholder="Clientes · octubre")
                    create = gr.Button("Crear proyecto")
                example = gr.Button("Cargar ejemplo completo", variant="secondary")
                uploads = gr.File(label="Añadir CSV al proyecto", file_count="multiple", file_types=[".csv"], type="filepath")
                with gr.Accordion("Opciones de lectura", open=False):
                    separator = gr.Dropdown(choices=[("Detectar automáticamente", "auto"), ("Coma", ","), ("Punto y coma", ";"), ("Tabulador", "\t"), ("Barra vertical", "|")], value="auto", label="Separador")
                    encoding = gr.Dropdown(choices=[("UTF-8", "utf-8-sig"), ("Windows-1252", "cp1252")], value="utf-8-sig", label="Codificación")
                add = gr.Button("Incorporar archivos", variant="primary")
                dataset = gr.Dropdown(choices=[], label="CSV activo", interactive=True)
                status = gr.Textbox(label="Estado", value="Empieza con el ejemplo o crea tu proyecto.", interactive=False, lines=3)
                gr.Markdown("**Límites:** 20 MiB por CSV · 100 000 filas · 100 columnas · 2 millones de celdas. Hasta 10 CSV por proyecto.")
            with gr.Column(scale=3, min_width=480):
                with gr.Tabs() as tabs:
                    with gr.Tab("Diagnóstico", id="diagnostic"):
                        diagnostic = gr.Markdown("### 02 / Conoce tus datos\nSelecciona un CSV o carga el ejemplo completo.")
                        profile_table = gr.Dataframe(label="Perfil de columnas · sugerencias orientativas", interactive=False)
                        original_table = gr.Dataframe(label="Original · primeros 100 registros", interactive=False)
                        original_download = gr.File(label="Descargar original intacto", interactive=False)
                        issues_before = gr.Dataframe(label="Incidencias del contrato guardado · primeras 100", interactive=False)
                    with gr.Tab("Reglas y limpieza", id="rules"):
                        gr.Markdown("### 03 / Diseña el contrato\nAplica una regla para incorporarla al JSON. El contrato solo se guarda al pulsar Guardar contrato o Ejecutar y guardar.")
                        with gr.Row():
                            column = gr.Dropdown(choices=[], label="Columna", interactive=True)
                            kind = gr.Dropdown(choices=[("Texto", "text"), ("Entero", "integer"), ("Decimal", "decimal"), ("Correo electrónico", "email"), ("Fecha", "date"), ("Booleano", "boolean")], value="text", label="Tipo")
                        with gr.Row():
                            required = gr.Checkbox(label="Valor obligatorio")
                            unique = gr.Checkbox(label="Valor único")
                            trim = gr.Checkbox(value=True, label="Recortar espacios")
                        with gr.Row():
                            casing = gr.Dropdown(choices=["Sin cambio", "Minúsculas", "Mayúsculas"], value="Sin cambio", label="Mayúsculas / minúsculas")
                            date_format = gr.Dropdown(choices=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"], value="%Y-%m-%d", label="Formato para fechas")
                        with gr.Row():
                            minimum = gr.Textbox(label="Mínimo numérico (opcional)", value="")
                            maximum = gr.Textbox(label="Máximo numérico (opcional)", value="")
                        with gr.Row():
                            fill_enabled = gr.Checkbox(label="Rellenar valores ausentes")
                            fill = gr.Textbox(label="Valor de relleno", value="")
                        with gr.Row():
                            dedupe = gr.Checkbox(label="Excluir duplicados, conservando la primera aparición")
                            subset = gr.Dropdown(choices=[], multiselect=True, label="Columnas para duplicados · vacío = fila completa")
                        apply_rule = gr.Button("Aplicar regla al JSON")
                        rules = gr.Code(label="Contrato declarativo · JSON", language="json", lines=18, interactive=True)
                        with gr.Row():
                            preview_button = gr.Button("Vista previa", variant="secondary")
                            execute_button = gr.Button("Ejecutar y guardar", variant="primary")
                        with gr.Accordion("Guardar, importar o restaurar reglas", open=False):
                            save_button = gr.Button("Guardar contrato sin ejecutar")
                            import_file = gr.File(label="Importar contrato JSON", file_types=[".json"], type="filepath")
                            import_button = gr.Button("Validar e importar reglas")
                            export_button = gr.Button("Exportar reglas JSON")
                            rules_download = gr.File(label="Descargar reglas", interactive=False)
                            reset_button = gr.Button("Restaurar contrato sugerido y vista original")
                    with gr.Tab("Comparación y resultados", id="comparison"):
                        gr.Markdown("### 04 / Revisa el efecto de tus reglas\nLa vista Después conserva todas las filas transformadas. Las descargas separan las válidas y las excluidas.")
                        preview_metrics = gr.HTML("")
                        with gr.Row():
                            before_table = gr.Dataframe(label="Antes · original, primeros 100", interactive=False)
                            after_table = gr.Dataframe(label="Después · transformado, primeros 100", interactive=False)
                        explanation = gr.Markdown("")
                        issues_after = gr.Dataframe(label="Incidencias tras limpiar · primeras 100", interactive=False)
                        commit_comparison = gr.Button("Ejecutar y guardar estas reglas", variant="primary")
                        downloads = gr.File(label="Archivos de la última ejecución guardada", file_count="multiple", interactive=False)
                        gr.Markdown("Las descargas incluyen CSV limpio, filas excluidas con su número de origen, incidencias, informe JSON y contrato. Las filas con errores no se corrigen inventando valores.")
                    with gr.Tab("Historial", id="history"):
                        gr.Markdown("### 05 / Una ejecución, una evidencia\nEl historial y los archivos se conservan tras reiniciar. Las huellas SHA-256 permiten comprobar entradas, reglas y resultados.")
                        refresh = gr.Button("Actualizar historial")
                        history_table = gr.Dataframe(label="Últimas 100 ejecuciones del proyecto", interactive=False)
                        run_choice = gr.Dropdown(choices=[], label="Abrir una ejecución", interactive=True)
                        history_files = gr.File(label="Descargar archivos históricos", file_count="multiple", interactive=False)
                        report = gr.Code(label="Informe verificable", language="json", interactive=False, lines=16)
        gr.HTML('<p class="studio-foot">Gradio presenta la interfaz; Python valida y transforma; SQLite conserva el historial. Sin modelos externos ni claves de API.<br>Los datos se guardan en este ordenador, dentro de <code>.private/data</code>. El repositorio solo incluye ejemplos sintéticos.</p>')

        dataset_outputs = [rules, column, original_table, profile_table, diagnostic, issues_before, original_download,
                           before_table, after_table, preview_metrics, downloads, status]
        comparison_outputs = [before_table, after_table, preview_metrics, issues_after, explanation]
        editor_outputs = [kind, required, trim, casing, fill_enabled, fill, minimum, maximum, date_format, unique, dedupe, subset]
        create.click(create_workspace, [project_name], [workspace, status])
        example.click(demo, [], [workspace, status])
        workspace.change(select_workspace, [workspace], [dataset, history_table, run_choice, status])
        add.click(add_files, [workspace, uploads, separator, encoding], [dataset, status])
        dataset.change(load_dataset, [dataset], dataset_outputs).then(read_column, [dataset, rules, column], editor_outputs)
        column.change(read_column, [dataset, rules, column], editor_outputs)
        apply_rule.click(apply_column, [dataset, rules, column, kind, required, trim, casing, fill_enabled, fill,
                                      minimum, maximum, date_format, unique, dedupe, subset], [rules, status])
        preview_button.click(preview, [dataset, rules], [*comparison_outputs, status, tabs])
        execute_button.click(execute, [workspace, dataset, rules], [*comparison_outputs, downloads, history_table, run_choice, report, status, tabs])
        commit_comparison.click(execute, [workspace, dataset, rules], [*comparison_outputs, downloads, history_table, run_choice, report, status, tabs])
        save_button.click(save_rules, [dataset, rules], [status])
        import_button.click(import_rules, [dataset, import_file], [rules, status])
        export_button.click(export_rules, [dataset, rules], [rules_download, status])
        reset_button.click(restore, [dataset], dataset_outputs).then(read_column, [dataset, rules, column], editor_outputs)
        refresh.click(lambda token: history_updates(token), [workspace], [history_table, run_choice])
        run_choice.change(show_run, [workspace, run_choice], [history_files, report])
        app.load(select_workspace, [workspace], [dataset, history_table, run_choice, status])
    return app
