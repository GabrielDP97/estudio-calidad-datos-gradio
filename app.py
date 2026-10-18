"""Punto de entrada; ejecución exclusivamente local."""
import argparse
import os
from pathlib import Path

os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
ROOT = Path(__file__).resolve().parent
os.environ["GRADIO_TEMP_DIR"] = str(ROOT / ".private" / "gradio-cache")

from quality_studio.ui import CSS, build_app
import gradio as gr


def main():
    parser = argparse.ArgumentParser(description="Dato: estudio local de calidad de datos")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    app = build_app()
    app.queue(default_concurrency_limit=1, max_size=8)
    app.launch(server_name="127.0.0.1", server_port=args.port, share=False, inbrowser=False,
               show_error=False, footer_links=[], max_file_size=20 * 1024 * 1024, css=CSS,
               theme=gr.themes.Soft(primary_hue="emerald", neutral_hue="slate", font=["Segoe UI", "Arial", "sans-serif"]),
               blocked_paths=[str(ROOT / ".git"), str(ROOT / ".venv"), str(ROOT / ".private" / "data" / "studio.sqlite3")])


if __name__ == "__main__":
    main()
