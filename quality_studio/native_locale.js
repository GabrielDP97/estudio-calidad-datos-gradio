// Gradio's built-in controls do not all react to a runtime locale change.
// Translate only known control text/attributes; never inspect CSV cells or code.
async (selected) => {
    if (!window.datoControlLocale) {
        const words = [
            ["Coloque el archivo aquí", "Drop file here", "Datei hier ablegen"],
            ["Haga clic para cargar", "Click to upload", "Zum Hochladen klicken"],
            ["- o -", "- or -", "- oder -"],
            ["Haga clic para cargar o arrastre archivos", "Click to upload or drop files", "Klicken oder Dateien hier ablegen"],
            ["Subir archivo", "File upload", "Datei hochladen"],
            ["Copiar datos de la tabla", "Copy table data", "Tabellendaten kopieren"],
            ["Pantalla completa", "Fullscreen", "Vollbild"],
            ["Salir de pantalla completa", "Exit fullscreen", "Vollbild verlassen"],
            ["Copiar", "Copy", "Kopieren"],
            ["Descargar", "Download", "Herunterladen"],
            ["Limpiar", "Clear", "Leeren"],
        ];
        const lookup = new Map(words.flatMap(row => row.map(value => [value, row])));
        let locale = "es";
        const translated = value => {
            const clean = value.trim();
            const row = lookup.get(clean);
            return row ? value.replace(clean, row[{es: 0, en: 1, de: 2}[locale]]) : value;
        };
        const update = () => {
            document.documentElement.lang = locale;
            // Upload instructions and native toolbar buttons contain no CSV data.
            for (const root of document.querySelectorAll('[data-testid="upload-text"], [role="toolbar"] button, button[aria-label], .cm-editor ~ button')) {
                const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
                while (walker.nextNode()) {
                    const node = walker.currentNode;
                    const value = translated(node.nodeValue);
                    if (value !== node.nodeValue) node.nodeValue = value;
                }
            }
            for (const element of document.querySelectorAll('[aria-label], [title]')) {
                for (const key of ['aria-label', 'title']) {
                    const old = element.getAttribute(key);
                    if (old) {
                        const value = translated(old);
                        if (value !== old) element.setAttribute(key, value);
                    }
                }
            }
        };
        const observer = new MutationObserver(update);
        observer.observe(document.body, {subtree: true, childList: true, characterData: true});
        window.datoControlLocale = code => {
            locale = ['es', 'en', 'de'].includes(code) ? code : 'es';
            update();
        };
    }
    window.datoControlLocale(selected);
    return [];
}
