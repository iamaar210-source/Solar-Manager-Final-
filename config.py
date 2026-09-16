import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Detect container / Railway
_IS_CONTAINER = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("PORT"))

if _IS_CONTAINER:
    # Prefer persistent Railway volume mounted at /data
    # Fallback to /tmp only if volume is not attached (data will be lost on restart)
    _volume = Path("/data")
    if _volume.exists() and os.access(_volume, os.W_OK):
        DATA_DIR = _volume / "solar_data"
    else:
        DATA_DIR = Path("/tmp/solar_data")
        print("WARNING: No writable /data volume — using /tmp (data will be lost on redeploy)", flush=True)
else:
    DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "exports").mkdir(parents=True, exist_ok=True)

if not _IS_CONTAINER:
    try:
        (BASE_DIR / "logs").mkdir(exist_ok=True)
        (BASE_DIR / "exports").mkdir(exist_ok=True)
    except Exception:
        pass

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "sa-solar-manager-secret-change-me-in-production")
    DATABASE_PATH = str(DATA_DIR / "solar_manager.db")
    UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "img")
    EXPORT_FOLDER = str(DATA_DIR / "exports")

    ALERT_PHONE = os.environ.get("ALERT_PHONE", "03107319742")
    ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "sasolarandelectricco@gmail.com")

    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")

    SMS_API_URL = os.environ.get("SMS_API_URL", "")
    SMS_API_KEY = os.environ.get("SMS_API_KEY", "")
    SMS_API_METHOD = os.environ.get("SMS_API_METHOD", "GET")

    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587") or "587")
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASS = os.environ.get("SMTP_PASS", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "")
