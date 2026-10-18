# Contribuir

Sigue la instalación del README y utiliza un entorno virtual. Mantén el motor independiente de Gradio y no añadas servicios externos necesarios para procesar datos.

Antes de proponer un cambio ejecuta:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m pip check
```

Comprueba también en el navegador la carga del ejemplo, la vista previa, una ejecución guardada y su historial. Si cambias las transformaciones, verifica que los originales siguen intactos y que la salida es reproducible. Actualiza límites y documentación cuando cambie el comportamiento.

Usa únicamente datos sintéticos en pruebas, ejemplos, capturas y pull requests. No subas `.private/`, `.venv/`, contratos reales con datos personales, credenciales ni exportaciones de usuarios. Explica en la pull request el problema, el comportamiento resultante y cómo lo has comprobado.
