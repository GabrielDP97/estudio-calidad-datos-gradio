# Historial de versiones

## 1.2.0 · 2026-10-18

- Selector de español, inglés y alemán, con traducciones locales.
- Cambio de idioma de controles, tablas, diagnósticos, métricas y errores sin perder el trabajo en edición.
- Idioma independiente por sesión; nombres, datos CSV, contratos y evidencias conservados.
- Pruebas de traducción, aislamiento de sesiones y limpieza real por HTTP en los tres idiomas.

## 1.1.0 · 2026-10-18

- CSV de hasta 100 MiB, 500 000 filas y 5 millones de celdas.
- Límite de subida de Gradio compartido con el motor, con mensajes y documentación actualizados.
- Corregida la representación de tablas vacías al crear un proyecto sin CSV.
- Se conservan las 100 columnas, las 20 000 incidencias y la vista previa de 100 registros.

## 1.0.0 · 2026-10-18

- Estudio local con Gradio, proyectos con varios CSV y contratos declarativos JSON.
- Perfil de columnas, tipos, ausentes, claves únicas y rangos.
- Limpieza por etapas, vista previa y exclusión de duplicados o filas con errores.
- Originales inmutables, huellas SHA-256, historial en SQLite y descargas completas.
- Importación/exportación y restauración de contratos, dos conjuntos sintéticos de demostración.
- Pruebas automatizadas, integración real de Gradio, documentación y arranque para Windows.
