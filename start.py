"""Production entrypoint for Railway. Always reads PORT from environment."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Railway injects PORT as an environment variable (never use literal "$PORT")
port = str(os.environ.get("PORT") or "8000").strip()
if not port.isdigit():
    port = "8000"

def main():
    try:
        import gunicorn  # noqa: F401
        from gunicorn.app.wsgiapp import run
        sys.argv = [
            "gunicorn",
            "wsgi:app",
            "--bind", f"0.0.0.0:{port}",
            "--workers", "1",
            "--threads", "4",
            "--timeout", "120",
            "--access-logfile", "-",
            "--error-logfile", "-",
        ]
        print(f"Starting gunicorn on 0.0.0.0:{port}", flush=True)
        run()
    except ModuleNotFoundError as e:
        print(f"WARNING: {e} — falling back to Flask server", flush=True)
        from app import create_app
        app = create_app()
        app.run(host="0.0.0.0", port=int(port), debug=False)

if __name__ == "__main__":
    main()
