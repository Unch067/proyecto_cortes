import os
import sys
import pandas  # noqa: F401
import plotly  # noqa: F401
import plotly.graph_objects  # noqa: F401
import plotly.subplots  # noqa: F401
import streamlit.web.cli as stcli


def resolver_ruta(ruta_relativa):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    if base_path not in sys.path:
        sys.path.insert(0, base_path)
    return os.path.join(base_path, ruta_relativa)


if __name__ == "__main__":
    ruta_app = resolver_ruta("app.py")
    sys.argv = [
        "streamlit",
        "run",
        ruta_app,
        "--global.developmentMode=false",
        "--server.headless=false",
    ]
    sys.exit(stcli.main())
