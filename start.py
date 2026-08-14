"""Railway / production entrypoint. Works with gunicorn or Flask fallback."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

port = os.environ.get("PORT", "8000")

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
        run()
    except ModuleNotFoundError:
        # Fallback if gunicorn not installed (Nixpacks misconfig)
        print("WARNING: gunicorn not found — using Flask development server", flush=True)
        from app import create_app
        app = create_app()
        app.run(host="0.0.0.0", port=int(port), debug=False)

if __name__ == "__main__":
    main()
