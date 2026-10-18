"""Local UI translations. ContextVar isolates concurrent browser sessions.

Only presentation text is translated: CSV contents, names, JSON contracts and
downloaded evidence are deliberately kept verbatim.
"""
from contextvars import ContextVar
import re

language = ContextVar("language", default="es")
LANGUAGES = [("Español", "es"), ("English", "en"), ("Deutsch", "de")]

# Spanish is the source language. Technical rule values remain language-neutral.
_ROWS = r"""
Proyecto ~~ Project ~~ Projekt
Crear un proyecto ~~ Create a project ~~ Projekt erstellen
Nombre del proyecto ~~ Project name ~~ Projektname
Clientes · octubre ~~ Customers · October ~~ Kunden · Oktober
Crear proyecto ~~ Create project ~~ Projekt erstellen
Cargar ejemplo completo ~~ Load full example ~~ Vollständiges Beispiel laden
Añadir CSV al proyecto ~~ Add CSV files to the project ~~ CSV-Dateien zum Projekt hinzufügen
Opciones de lectura ~~ Reading options ~~ Importoptionen
Separador ~~ Delimiter ~~ Trennzeichen
Detectar automáticamente ~~ Detect automatically ~~ Automatisch erkennen
Coma ~~ Comma ~~ Komma
Punto y coma ~~ Semicolon ~~ Semikolon
Tabulador ~~ Tab ~~ Tabulator
Barra vertical ~~ Pipe ~~ Senkrechter Strich
Codificación ~~ Encoding ~~ Zeichenkodierung
Incorporar archivos ~~ Add files ~~ Dateien hinzufügen
CSV activo ~~ Active CSV ~~ Aktive CSV-Datei
Estado ~~ Status ~~ Status
Empieza con el ejemplo o crea tu proyecto. ~~ Start with the example or create your project. ~~ Lade das Beispiel oder erstelle ein Projekt.
Diagnóstico ~~ Diagnostics ~~ Diagnose
Perfil de columnas · sugerencias orientativas ~~ Column profile · indicative suggestions ~~ Spaltenprofil · unverbindliche Vorschläge
Original · primeros 100 registros ~~ Original · first 100 records ~~ Original · erste 100 Datensätze
Descargar original intacto ~~ Download unchanged original ~~ Unverändertes Original herunterladen
Incidencias del contrato guardado · primeras 100 ~~ Saved contract issues · first 100 ~~ Probleme des gespeicherten Regelwerks · erste 100
Reglas y limpieza ~~ Rules and cleaning ~~ Regeln und Bereinigung
Columna ~~ Column ~~ Spalte
Tipo ~~ Type ~~ Typ
Texto ~~ Text ~~ Text
Entero ~~ Integer ~~ Ganzzahl
Decimal ~~ Decimal ~~ Dezimalzahl
Correo electrónico ~~ Email ~~ E-Mail
Fecha ~~ Date ~~ Datum
Booleano ~~ Boolean ~~ Wahrheitswert
Valor obligatorio ~~ Required value ~~ Pflichtwert
Valor único ~~ Unique value ~~ Eindeutiger Wert
Recortar espacios ~~ Trim whitespace ~~ Leerzeichen entfernen
Mayúsculas / minúsculas ~~ Letter case ~~ Groß-/Kleinschreibung
Sin cambio ~~ Unchanged ~~ Unverändert
Minúsculas ~~ Lowercase ~~ Kleinbuchstaben
Mayúsculas ~~ Uppercase ~~ Großbuchstaben
Formato para fechas ~~ Date format ~~ Datumsformat
Mínimo numérico (opcional) ~~ Numeric minimum (optional) ~~ Numerisches Minimum (optional)
Máximo numérico (opcional) ~~ Numeric maximum (optional) ~~ Numerisches Maximum (optional)
Rellenar valores ausentes ~~ Fill missing values ~~ Fehlende Werte auffüllen
Valor de relleno ~~ Fill value ~~ Ersatzwert
Excluir duplicados, conservando la primera aparición ~~ Exclude duplicates, keeping the first occurrence ~~ Duplikate ausschließen, erstes Vorkommen behalten
Columnas para duplicados · vacío = fila completa ~~ Duplicate key columns · empty = entire row ~~ Duplikatschlüssel · leer = gesamte Zeile
Aplicar regla al JSON ~~ Apply rule to JSON ~~ Regel in JSON übernehmen
Contrato declarativo · JSON ~~ Declarative contract · JSON ~~ Deklaratives Regelwerk · JSON
Vista previa ~~ Preview ~~ Vorschau
Ejecutar y guardar ~~ Run and save ~~ Ausführen und speichern
Guardar, importar o restaurar reglas ~~ Save, import or restore rules ~~ Regeln speichern, importieren oder zurücksetzen
Guardar contrato sin ejecutar ~~ Save contract without running ~~ Regelwerk ohne Ausführung speichern
Importar contrato JSON ~~ Import JSON contract ~~ JSON-Regelwerk importieren
Validar e importar reglas ~~ Validate and import rules ~~ Regeln prüfen und importieren
Exportar reglas JSON ~~ Export JSON rules ~~ JSON-Regeln exportieren
Descargar reglas ~~ Download rules ~~ Regeln herunterladen
Restaurar contrato sugerido y vista original ~~ Restore suggested contract and original view ~~ Vorgeschlagenes Regelwerk und Originalansicht wiederherstellen
Comparación y resultados ~~ Comparison and results ~~ Vergleich und Ergebnisse
Antes · original, primeros 100 ~~ Before · original, first 100 ~~ Vorher · Original, erste 100
Después · transformado, primeros 100 ~~ After · transformed, first 100 ~~ Nachher · bearbeitet, erste 100
Incidencias tras limpiar · primeras 100 ~~ Issues after cleaning · first 100 ~~ Probleme nach der Bereinigung · erste 100
Ejecutar y guardar estas reglas ~~ Run and save these rules ~~ Diese Regeln ausführen und speichern
Archivos de la última ejecución guardada ~~ Files from the last saved run ~~ Dateien der letzten gespeicherten Ausführung
Historial ~~ History ~~ Verlauf
Actualizar historial ~~ Refresh history ~~ Verlauf aktualisieren
Últimas 100 ejecuciones del proyecto ~~ Last 100 project runs ~~ Letzte 100 Projektausführungen
Abrir una ejecución ~~ Open a run ~~ Ausführung öffnen
Descargar archivos históricos ~~ Download historical files ~~ Frühere Dateien herunterladen
Informe verificable ~~ Verifiable report ~~ Überprüfbarer Bericht
Sin datos ~~ No data ~~ Keine Daten
Fecha UTC ~~ UTC date ~~ UTC-Datum
Válidas ~~ Valid ~~ Gültig
Excluidas ~~ Excluded ~~ Ausgeschlossen
SHA-256 salida (inicio) ~~ Output SHA-256 (prefix) ~~ Ausgabe-SHA-256 (Anfang)
Tipo sugerido ~~ Suggested type ~~ Vorgeschlagener Typ
Filas ~~ Rows ~~ Zeilen
Ausentes ~~ Missing ~~ Fehlend
Distintos ~~ Distinct ~~ Verschieden
Ejemplos ~~ Examples ~~ Beispiele
Fila CSV ~~ CSV row ~~ CSV-Zeile
Valor ~~ Value ~~ Wert
Incidencia ~~ Issue ~~ Problem
Filas de entrada ~~ Input rows ~~ Eingabezeilen
Filas válidas ~~ Valid rows ~~ Gültige Zeilen
Filas excluidas ~~ Excluded rows ~~ Ausgeschlossene Zeilen
Celdas modificadas ~~ Modified cells ~~ Geänderte Zellen
Proyecto creado. Añade uno o varios CSV. ~~ Project created. Add one or more CSV files. ~~ Projekt erstellt. Füge eine oder mehrere CSV-Dateien hinzu.
Selecciona un CSV para revisar su contrato y diagnóstico. ~~ Select a CSV to review its contract and diagnostics. ~~ Wähle eine CSV-Datei, um Regelwerk und Diagnose zu prüfen.
Selecciona un CSV para ver su diagnóstico. ~~ Select a CSV to view its diagnostics. ~~ Wähle eine CSV-Datei für die Diagnose.
Ejemplo creado con dos CSV y contratos preparados. Abre Reglas y limpieza para previsualizarlo. ~~ Example created with two CSV files and prepared contracts. Open Rules and cleaning to preview it. ~~ Beispiel mit zwei CSV-Dateien und vorbereiteten Regelwerken erstellt. Öffne Regeln und Bereinigung für die Vorschau.
Original cargado. Edita las reglas y pulsa Vista previa; no se ha guardado una ejecución. ~~ Original loaded. Edit the rules and click Preview; no run has been saved. ~~ Original geladen. Bearbeite die Regeln und klicke auf Vorschau; es wurde keine Ausführung gespeichert.
Regla incorporada al JSON. Pulsa Vista previa para comprobar su efecto. ~~ Rule added to JSON. Click Preview to check its effect. ~~ Regel in JSON übernommen. Klicke auf Vorschau, um die Wirkung zu prüfen.
Vista previa calculada sobre el original. Todavía no se ha guardado ninguna ejecución. ~~ Preview calculated from the original. No run has been saved yet. ~~ Vorschau aus dem Original berechnet. Es wurde noch keine Ausführung gespeichert.
Contrato guardado para este CSV. El historial previo se conserva. ~~ Contract saved for this CSV. Previous history is preserved. ~~ Regelwerk für diese CSV-Datei gespeichert. Der bisherige Verlauf bleibt erhalten.
Reglas importadas a la vista de edición; revisa y guarda cuando quieras. ~~ Rules imported into the editor; review and save when ready. ~~ Regeln in den Editor importiert; prüfe und speichere sie bei Bedarf.
Reglas preparadas para descargar. ~~ Rules ready to download. ~~ Regeln zum Herunterladen bereit.
{count} archivos incorporados o ya existentes. ~~ {count} files added or already present. ~~ {count} Dateien hinzugefügt oder bereits vorhanden.
Ejecución guardada: {id}. Salida SHA-256: {hash} ~~ Run saved: {id}. Output SHA-256: {hash} ~~ Ausführung gespeichert: {id}. Ausgabe-SHA-256: {hash}
Valor obligatorio ausente ~~ Required value missing ~~ Pflichtwert fehlt
Formato incorrecto: {type} ~~ Invalid format: {type} ~~ Ungültiges Format: {type}
Valor fuera del rango permitido ~~ Value outside the allowed range ~~ Wert außerhalb des zulässigen Bereichs
Clave única duplicada (se conserva la primera aparición) ~~ Duplicate unique key (first occurrence kept) ~~ Doppelter eindeutiger Schlüssel (erstes Vorkommen bleibt erhalten)
Duplicado excluido por las reglas ~~ Duplicate excluded by the rules ~~ Duplikat durch Regeln ausgeschlossen
Rellenar ausentes ~~ Fill missing values ~~ Fehlende Werte auffüllen
Sustituir valores ~~ Replace values ~~ Werte ersetzen
Excluir duplicados ~~ Exclude duplicates ~~ Duplikate ausschließen
No se pudo leer o guardar el proyecto. Comprueba el espacio libre y los permisos; el original se conserva. ~~ Could not read or save the project. Check free disk space and permissions; the original is preserved. ~~ Das Projekt konnte nicht gelesen oder gespeichert werden. Prüfe Speicherplatz und Berechtigungen; das Original bleibt erhalten.
Crea o selecciona un proyecto antes de añadir archivos. ~~ Create or select a project before adding files. ~~ Erstelle oder wähle ein Projekt, bevor du Dateien hinzufügst.
Selecciona entre 1 y 10 CSV. ~~ Select between 1 and 10 CSV files. ~~ Wähle zwischen 1 und 10 CSV-Dateien.
Selecciona una columna. ~~ Select a column. ~~ Wähle eine Spalte.
El mínimo y máximo deben ser números con punto decimal. ~~ Minimum and maximum must be numbers with a decimal point. ~~ Minimum und Maximum müssen Zahlen mit Dezimalpunkt sein.
El CSV no pertenece al proyecto seleccionado. ~~ The CSV does not belong to the selected project. ~~ Die CSV-Datei gehört nicht zum ausgewählten Projekt.
Selecciona reglas JSON de hasta 100 KB. ~~ Select JSON rules up to 100 KB. ~~ Wähle JSON-Regeln mit höchstens 100 KB.
El JSON debe estar codificado en UTF-8. ~~ JSON must be encoded in UTF-8. ~~ JSON muss UTF-8-kodiert sein.
La ejecución no pertenece al proyecto seleccionado. ~~ The run does not belong to the selected project. ~~ Die Ausführung gehört nicht zum ausgewählten Projekt.
El archivo supera {size} MiB. ~~ The file exceeds {size} MiB. ~~ Die Datei überschreitet {size} MiB.
Pon un nombre de proyecto de entre 1 y 80 caracteres. ~~ Enter a project name between 1 and 80 characters. ~~ Gib einen Projektnamen mit 1 bis 80 Zeichen ein.
Selecciona un proyecto existente. ~~ Select an existing project. ~~ Wähle ein vorhandenes Projekt.
Selecciona un CSV del proyecto. ~~ Select a CSV from the project. ~~ Wähle eine CSV-Datei aus dem Projekt.
Falta la copia original de este CSV. ~~ The original copy of this CSV is missing. ~~ Die Originalkopie dieser CSV-Datei fehlt.
La copia original supera {size} MiB. Carga un CSV dentro del límite. ~~ The original copy exceeds {size} MiB. Upload a CSV within the limit. ~~ Die Originalkopie überschreitet {size} MiB. Lade eine CSV-Datei innerhalb des Limits hoch.
La copia original ha cambiado fuera de la aplicación. Carga el archivo de nuevo como otra versión. ~~ The original copy changed outside the app. Upload the file again as another version. ~~ Die Originalkopie wurde außerhalb der Anwendung geändert. Lade die Datei als neue Version hoch.
Usa un nombre de archivo CSV sin rutas, de hasta 180 caracteres. ~~ Use a CSV filename without paths, up to 180 characters. ~~ Verwende einen CSV-Dateinamen ohne Pfadangabe mit höchstens 180 Zeichen.
Cada proyecto admite hasta 10 CSV distintos. Crea otro proyecto. ~~ Each project supports up to 10 different CSV files. Create another project. ~~ Jedes Projekt erlaubt bis zu 10 verschiedene CSV-Dateien. Erstelle ein weiteres Projekt.
La ejecución no existe. ~~ The run does not exist. ~~ Die Ausführung existiert nicht.
Faltan archivos de esta ejecución; no se ha modificado el original. ~~ Files from this run are missing; the original has not been modified. ~~ Dateien dieser Ausführung fehlen; das Original wurde nicht geändert.
El CSV está vacío o supera {size} MiB. ~~ The CSV is empty or exceeds {size} MiB. ~~ Die CSV-Datei ist leer oder überschreitet {size} MiB.
Codificación no admitida. ~~ Unsupported encoding. ~~ Nicht unterstützte Zeichenkodierung.
No se pudo leer la codificación. Prueba Windows-1252 si el CSV no es UTF-8. ~~ Could not read the encoding. Try Windows-1252 if the CSV is not UTF-8. ~~ Die Zeichenkodierung konnte nicht gelesen werden. Versuche Windows-1252, falls die CSV-Datei nicht UTF-8-kodiert ist.
El CSV contiene datos binarios. ~~ The CSV contains binary data. ~~ Die CSV-Datei enthält Binärdaten.
Separador no admitido. ~~ Unsupported delimiter. ~~ Nicht unterstütztes Trennzeichen.
Usa entre 1 y 100 columnas con nombres no vacíos de hasta 120 caracteres. ~~ Use 1 to 100 columns with nonempty names up to 120 characters. ~~ Verwende 1 bis 100 Spalten mit nicht leeren Namen und höchstens 120 Zeichen.
Hay nombres de columna duplicados. ~~ Duplicate column names found. ~~ Doppelte Spaltennamen gefunden.
El registro {row} tiene un número de columnas incorrecto. ~~ Record {row} has an incorrect number of columns. ~~ Datensatz {row} hat eine falsche Spaltenanzahl.
El CSV supera {rows} filas o {cells} celdas. ~~ The CSV exceeds {rows} rows or {cells} cells. ~~ Die CSV-Datei überschreitet {rows} Zeilen oder {cells} Zellen.
El CSV solo contiene la cabecera; añade al menos una fila. ~~ The CSV only contains a header; add at least one row. ~~ Die CSV-Datei enthält nur eine Kopfzeile; füge mindestens eine Datenzeile hinzu.
CSV incompleto, comillas incorrectas o campo demasiado grande. ~~ Incomplete CSV, incorrect quotation marks or field too large. ~~ Unvollständige CSV-Datei, fehlerhafte Anführungszeichen oder zu großes Feld.
Las reglas superan 100 KB. ~~ The rules exceed 100 KB. ~~ Die Regeln überschreiten 100 KB.
Las reglas no contienen un JSON válido. ~~ The rules do not contain valid JSON. ~~ Die Regeln enthalten kein gültiges JSON.
Las reglas deben ser un objeto JSON con version: 1. ~~ The rules must be a JSON object with version: 1. ~~ Die Regeln müssen ein JSON-Objekt mit version: 1 sein.
Hay opciones de reglas desconocidas. ~~ Unknown rule options found. ~~ Unbekannte Regeloptionen gefunden.
Las reglas mencionan columnas que no existen. ~~ The rules refer to columns that do not exist. ~~ Die Regeln verweisen auf nicht vorhandene Spalten.
Regla no válida en {name}. ~~ Invalid rule in {name}. ~~ Ungültige Regel in {name}.
Tipo o formato de fecha no admitido en {name}. ~~ Unsupported type or date format in {name}. ~~ Nicht unterstützter Typ oder Datumsformat in {name}.
{flag} debe ser verdadero o falso en {name}. ~~ {flag} must be true or false in {name}. ~~ {flag} muss in {name} true oder false sein.
No se pueden aplicar mayúsculas y minúsculas a la vez en {name}. ~~ Cannot apply uppercase and lowercase at the same time in {name}. ~~ Groß- und Kleinschreibung können in {name} nicht gleichzeitig angewendet werden.
El relleno debe ser un texto de hasta 10 000 caracteres. ~~ The fill value must be text up to 10 000 characters. ~~ Der Ersatzwert muss Text mit höchstens 10 000 Zeichen sein.
Las sustituciones deben ser un objeto de textos, con un máximo de 100 entradas. ~~ Replacements must be an object of strings with at most 100 entries. ~~ Ersetzungen müssen ein Objekt aus Texten mit höchstens 100 Einträgen sein.
Los límites numéricos deben ser números finitos. ~~ Numeric limits must be finite numbers. ~~ Numerische Grenzen müssen endliche Zahlen sein.
Los límites mínimo/máximo requieren un tipo numérico. ~~ Minimum/maximum limits require a numeric type. ~~ Minimum-/Maximum-Grenzen erfordern einen numerischen Typ.
El mínimo no puede superar al máximo. ~~ The minimum cannot exceed the maximum. ~~ Das Minimum darf das Maximum nicht überschreiten.
unique debe ser una lista de claves. ~~ unique must be a list of keys. ~~ unique muss eine Liste von Schlüsseln sein.
Cada clave única debe contener columnas existentes, sin repetir. ~~ Each unique key must contain existing columns without repetition. ~~ Jeder eindeutige Schlüssel muss vorhandene Spalten ohne Wiederholung enthalten.
La clave de duplicados debe contener columnas existentes, sin repetir. ~~ The duplicate key must contain existing columns without repetition. ~~ Der Duplikatschlüssel muss vorhandene Spalten ohne Wiederholung enthalten.
drop_duplicates debe ser verdadero o falso. ~~ drop_duplicates must be true or false. ~~ drop_duplicates muss true oder false sein.
missing_values debe ser una lista de textos (máximo 100). ~~ missing_values must be a list of strings (at most 100). ~~ missing_values muss eine Liste von Texten sein (höchstens 100).
Hay más de 20 000 incidencias. Divide el CSV o revisa las reglas. ~~ There are more than 20 000 issues. Split the CSV or review the rules. ~~ Es gibt mehr als 20 000 Probleme. Teile die CSV-Datei auf oder prüfe die Regeln.
"""

CATALOG = {row[0]: dict(zip(("es", "en", "de"), row))
           for line in _ROWS.strip().splitlines() if (row := line.split(" ~~ "))}


def add(source, english, german):
    CATALOG[source] = dict(es=source, en=english, de=german)


add("### 01 / Tu espacio de trabajo", "### 01 / Your workspace", "### 01 / Dein Arbeitsbereich")
add("### 02 / Conoce tus datos\nSelecciona un CSV o carga el ejemplo completo.",
    "### 02 / Understand your data\nSelect a CSV or load the full example.",
    "### 02 / Lerne deine Daten kennen\nWähle eine CSV-Datei oder lade das vollständige Beispiel.")
add("### 03 / Diseña el contrato\nAplica una regla para incorporarla al JSON. El contrato solo se guarda al pulsar Guardar contrato o Ejecutar y guardar.",
    "### 03 / Design the contract\nApply a rule to add it to JSON. The contract is only saved when you click Save contract or Run and save.",
    "### 03 / Definiere das Regelwerk\nÜbernimm eine Regel in JSON. Das Regelwerk wird erst mit Regelwerk speichern oder Ausführen und speichern gespeichert.")
add("### 04 / Revisa el efecto de tus reglas\nLa vista Después conserva todas las filas transformadas. Las descargas separan las válidas y las excluidas.",
    "### 04 / Review the effect of your rules\nThe After view keeps all transformed rows. Downloads separate valid and excluded rows.",
    "### 04 / Prüfe die Wirkung deiner Regeln\nDie Nachher-Ansicht enthält alle bearbeiteten Zeilen. Downloads trennen gültige und ausgeschlossene Zeilen.")
add("### 05 / Una ejecución, una evidencia\nEl historial y los archivos se conservan tras reiniciar. Las huellas SHA-256 permiten comprobar entradas, reglas y resultados.",
    "### 05 / Every run leaves evidence\nHistory and files persist after restarting. SHA-256 hashes let you verify inputs, rules and results.",
    "### 05 / Jede Ausführung ist nachvollziehbar\nVerlauf und Dateien bleiben nach einem Neustart erhalten. SHA-256-Prüfsummen ermöglichen die Prüfung von Eingaben, Regeln und Ergebnissen.")
add("Las descargas incluyen CSV limpio, filas excluidas con su número de origen, incidencias, informe JSON y contrato. Las filas con errores no se corrigen inventando valores.",
    "Downloads include clean CSV, excluded rows with their original row numbers, issues, JSON report and contract. Rows with errors are not corrected by inventing values.",
    "Downloads enthalten die bereinigte CSV-Datei, ausgeschlossene Zeilen mit ursprünglicher Zeilennummer, Probleme, JSON-Bericht und Regelwerk. Fehlerhafte Zeilen werden nicht mit erfundenen Werten korrigiert.")
add("**Límites:** {size} MiB por CSV · {rows} filas · {columns} columnas · {cells} celdas. Hasta 10 CSV por proyecto.",
    "**Limits:** {size} MiB per CSV · {rows} rows · {columns} columns · {cells} cells. Up to 10 CSV files per project.",
    "**Grenzen:** {size} MiB pro CSV · {rows} Zeilen · {columns} Spalten · {cells} Zellen. Bis zu 10 CSV-Dateien pro Projekt.")
add("**{rows} filas · {columns} columnas · {duplicates} filas idénticas repetidas · {issues} incidencias del contrato guardado.**\n\nLos tipos sugeridos son orientativos. Las tablas muestran hasta 100 registros. Original SHA-256: `{hash}`",
    "**{rows} rows · {columns} columns · {duplicates} repeated identical rows · {issues} saved contract issues.**\n\nSuggested types are indicative. Tables show up to 100 records. Original SHA-256: `{hash}`",
    "**{rows} Zeilen · {columns} Spalten · {duplicates} wiederholte identische Zeilen · {issues} Probleme des gespeicherten Regelwerks.**\n\nVorgeschlagene Typen sind unverbindlich. Tabellen zeigen bis zu 100 Datensätze. Original-SHA-256: `{hash}`")
add("Incidencias antes: {before} · Incidencias después: {after}. Las filas excluidas incluyen errores pendientes y duplicados descartados; las incidencias se cuentan por celda o restricción.\n\nEtapas: {stages}.",
    "Issues before: {before} · Issues after: {after}. Excluded rows include unresolved errors and discarded duplicates; issues are counted per cell or constraint.\n\nStages: {stages}.",
    "Probleme vorher: {before} · Probleme nachher: {after}. Ausgeschlossene Zeilen umfassen ungelöste Fehler und entfernte Duplikate; Probleme werden je Zelle oder Bedingung gezählt.\n\nSchritte: {stages}.")

HERO = '<div class="studio-hero"><span class="local-tag">● Local · Sin servicios de pago</span><div class="eyebrow">DATO / ESTUDIO DE CALIDAD</div><h1>Datos que merecen confianza.</h1><p>Encuentra errores, prepara reglas y revisa cada cambio antes de guardar una copia limpia. Tus originales siempre se conservan.</p></div>'
add(HERO,
    '<div class="studio-hero"><span class="local-tag">● Local · No paid services</span><div class="eyebrow">DATO / DATA QUALITY STUDIO</div><h1>Data you can trust.</h1><p>Find errors, prepare rules and review every change before saving a clean copy. Your originals are always preserved.</p></div>',
    '<div class="studio-hero"><span class="local-tag">● Lokal · Ohne kostenpflichtige Dienste</span><div class="eyebrow">DATO / DATENQUALITÄTSSTUDIO</div><h1>Daten, denen du vertrauen kannst.</h1><p>Finde Fehler, definiere Regeln und prüfe jede Änderung, bevor du eine bereinigte Kopie speicherst. Deine Originale bleiben immer erhalten.</p></div>')
FOOTER = '<p class="studio-foot">Gradio presenta la interfaz; Python valida y transforma; SQLite conserva el historial. Sin modelos externos ni claves de API.<br>Los datos se guardan en este ordenador, dentro de <code>.private/data</code>. El repositorio solo incluye ejemplos sintéticos.</p>'
add(FOOTER,
    '<p class="studio-foot">Gradio provides the interface; Python validates and transforms; SQLite stores history. No external models or API keys.<br>Data is stored on this computer in <code>.private/data</code>. The repository only includes synthetic examples.</p>',
    '<p class="studio-foot">Gradio stellt die Oberfläche bereit; Python prüft und verarbeitet; SQLite speichert den Verlauf. Ohne externe Modelle oder API-Schlüssel.<br>Die Daten bleiben auf diesem Computer in <code>.private/data</code>. Das Repository enthält nur synthetische Beispiele.</p>')

_LOOKUP = {value: source for source, values in CATALOG.items() for value in values.values()}
_TEMPLATES = []
for source, values in CATALOG.items():
    if "{" not in source:
        continue
    for value in values.values():
        parts = re.split(r"(\{\w+\})", value)
        pattern = "".join(f"(?P<{part[1:-1]}>.+?)" if part.startswith("{") else re.escape(part) for part in parts)
        _TEMPLATES.append((re.compile(pattern, re.DOTALL), source))


def tr(text, locale=None):
    """Translate a known whole UI message, preserving captured user values."""
    locale = locale or language.get()
    if not isinstance(text, str) or not text:
        return text
    source = _LOOKUP.get(text)
    if source:
        return CATALOG[source][locale]
    for pattern, source in _TEMPLATES:
        match = pattern.fullmatch(text)
        if match:
            values = match.groupdict()
            if "stages" in values:
                values["stages"] = ", ".join(tr(k, locale) + ": " + v for k, v in
                                             (item.rsplit(": ", 1) for item in values["stages"].split(", ") if ": " in item))
            return CATALOG[source][locale].format(**values)
    return text


def type_label(value):
    return tr({"text": "Texto", "integer": "Entero", "decimal": "Decimal", "email": "Correo electrónico",
               "date": "Fecha", "boolean": "Booleano"}.get(value, value))


def native_locale_js():
    """Local fallback for native upload instructions and accessible tooltips."""
    from pathlib import Path
    return Path(__file__).with_name("native_locale.js").read_text(encoding="utf-8")
