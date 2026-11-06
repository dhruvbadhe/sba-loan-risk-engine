"""Serve the existing API and Streamlit dashboard from one ASGI application."""

from pathlib import Path
import os

# Vendored packages can otherwise be mistaken for a Streamlit development checkout.
os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false")

from streamlit import App, config

from app.main import app

config.get_config_options(force_reparse=True)
dashboard = App(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


app.router.lifespan_context = dashboard.lifespan()
# API routes are registered first; remaining paths belong to Streamlit.
app.mount("/", dashboard)
