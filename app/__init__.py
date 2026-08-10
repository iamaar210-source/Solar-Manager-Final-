from flask import Flask
from pathlib import Path
from config import Config

def create_app():
    base = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(base / "templates"),
        static_folder=str(base / "static"),
    )
    app.config.from_object(Config)

    # Ensure secret key is set
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = "sa-solar-manager-secret-change-me-in-production"

    from app.routes import bp
    app.register_blueprint(bp)

    return app
