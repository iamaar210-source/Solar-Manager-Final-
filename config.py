import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
(BASE_DIR / "logs").mkdir(exist_ok=True)
(BASE_DIR / "exports").mkdir(exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "sa-solar-manager-secret-change-me-in-production")
    DATABASE_PATH = str(DATA_DIR / "solar_manager.db")
    UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "img")
    EXPORT_FOLDER = str(BASE_DIR / "exports")

    # Owner alert destinations
    ALERT_PHONE = os.environ.get("ALERT_PHONE", "03107319742")
    ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "sasolarandelectricco@gmail.com")

    # Twilio SMS (optional)
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")

    # Generic HTTP SMS API (local Pakistani gateways)
    # Example URL: https://your-sms-provider.com/api/send?key={key}&to={phone}&message={message}
    SMS_API_URL = os.environ.get("SMS_API_URL", "")
    SMS_API_KEY = os.environ.get("SMS_API_KEY", "")
    SMS_API_METHOD = os.environ.get("SMS_API_METHOD", "GET")

    # SMTP Email (optional – Gmail, etc.)
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASS = os.environ.get("SMTP_PASS", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "")
