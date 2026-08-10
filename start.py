import os
import sys

port = os.environ.get("PORT", "8000")
sys.argv = [
    "gunicorn",
    "wsgi:app",
    "--bind",
    f"0.0.0.0:{port}",
    "--workers",
    "1",
]

from gunicorn.app.wsgiapp import run
run()
