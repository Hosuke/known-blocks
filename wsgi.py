"""WSGI entry point for production deployment."""
from pathlib import Path
from tools.web import create_web_app

app = create_web_app(Path("."))
