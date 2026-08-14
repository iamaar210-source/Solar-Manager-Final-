"""
SMS + Email alert service for Solar Manager.
Alerts are sent ONLY on user login (as requested).

Supports:
  1. Twilio SMS
  2. Generic HTTP SMS API (for local Pakistani gateways)
  3. SMTP Email
  4. Log-only mode when no API keys are configured
"""
import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("solar_alerts")

# Ensure logs folder exists
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "alerts.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


class AlertService:
    def __init__(self):
        # Twilio
        self.twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        self.twilio_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.twilio_from = os.environ.get("TWILIO_FROM_NUMBER", "")  # e.g. +1234567890

        # Generic HTTP SMS API (local Pakistani providers)
        # Example: https://api.example.com/send?key=XXX&to={phone}&message={message}
        self.sms_api_url = os.environ.get("SMS_API_URL", "")
        self.sms_api_key = os.environ.get("SMS_API_KEY", "")
        self.sms_api_method = os.environ.get("SMS_API_METHOD", "GET").upper()  # GET or POST

        # Owner alert destinations
        self.alert_phone = os.environ.get("ALERT_PHONE", "03107319742")
        self.alert_email = os.environ.get("ALERT_EMAIL", "sasolarandelectricco@gmail.com")

        # SMTP Email
        self.smtp_host = os.environ.get("SMTP_HOST", "")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_pass = os.environ.get("SMTP_PASS", "")
        self.smtp_from = os.environ.get("SMTP_FROM", self.smtp_user or self.alert_email)

    def send_login_alert(self, username: str, full_name: str, location: str, ip: str = ""):
        """Called on every successful login. Sends SMS + Email to Owner."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        loc_label = location or "Owner / All"
        msg = (
            f"Solar Manager Login Alert\n"
            f"User: {full_name} ({username})\n"
            f"Location: {loc_label}\n"
            f"Time: {now}\n"
            f"IP: {ip or 'N/A'}"
        )
        subject = f"Login Alert: {username}"

        sms_ok = self._send_sms(self.alert_phone, msg)
        email_ok = self._send_email(self.alert_email, subject, msg)

        logger.info(
            "Login alert for %s | SMS=%s Email=%s | to phone=%s email=%s",
            username, sms_ok, email_ok, self.alert_phone, self.alert_email
        )
        return {"sms": sms_ok, "email": email_ok}

    def _send_sms(self, phone: str, message: str) -> bool:
        if not phone:
            return False
        phone = self._normalize_phone(phone)

        # 1) Twilio
        if self.twilio_sid and self.twilio_token and self.twilio_from:
            return self._send_twilio(phone, message)

        # 2) Generic HTTP API
        if self.sms_api_url and self.sms_api_key:
            return self._send_http_sms(phone, message)

        # 3) Log only (no keys configured)
        logger.info("[SMS LOG ONLY] To: %s | Message: %s", phone, message.replace("\n", " | "))
        print(f"[SMS LOG] To {phone}: {message[:80]}...")
        return True  # treat as success in demo mode

    def _send_twilio(self, phone: str, message: str) -> bool:
        try:
            from urllib.request import Request, urlopen
            from urllib.parse import urlencode
            import base64

            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
            data = urlencode({
                "To": phone if phone.startswith("+") else f"+92{phone.lstrip('0')}",
                "From": self.twilio_from,
                "Body": message,
            }).encode()
            auth = base64.b64encode(f"{self.twilio_sid}:{self.twilio_token}".encode()).decode()
            req = Request(url, data=data, method="POST")
            req.add_header("Authorization", f"Basic {auth}")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            with urlopen(req, timeout=15) as resp:
                ok = 200 <= resp.status < 300
                logger.info("Twilio SMS status=%s", resp.status)
                return ok
        except Exception as e:
            logger.error("Twilio SMS failed: %s", e)
            return False

    def _send_http_sms(self, phone: str, message: str) -> bool:
        """Generic HTTP SMS gateway. URL may contain {phone}, {message}, {key} placeholders."""
        try:
            from urllib.request import Request, urlopen
            from urllib.parse import urlencode, quote

            url = self.sms_api_url
            url = url.replace("{phone}", quote(phone)).replace("{message}", quote(message))
            url = url.replace("{key}", quote(self.sms_api_key))

            if self.sms_api_method == "POST":
                data = urlencode({
                    "phone": phone,
                    "to": phone,
                    "message": message,
                    "text": message,
                    "key": self.sms_api_key,
                    "api_key": self.sms_api_key,
                }).encode()
                req = Request(url, data=data, method="POST")
                req.add_header("Content-Type", "application/x-www-form-urlencoded")
            else:
                # If placeholders not used, append query params
                if "{phone}" not in self.sms_api_url:
                    sep = "&" if "?" in url else "?"
                    url = f"{url}{sep}to={quote(phone)}&message={quote(message)}&key={quote(self.sms_api_key)}"
                req = Request(url, method="GET")

            with urlopen(req, timeout=15) as resp:
                ok = 200 <= resp.status < 300
                logger.info("HTTP SMS status=%s url=%s", resp.status, url[:80])
                return ok
        except Exception as e:
            logger.error("HTTP SMS failed: %s", e)
            return False

    def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        if not to_email:
            return False

        if not self.smtp_host or not self.smtp_user:
            logger.info("[EMAIL LOG ONLY] To: %s | Subject: %s | %s", to_email, subject, body.replace("\n", " | "))
            print(f"[EMAIL LOG] To {to_email}: {subject}")
            return True

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = self.smtp_from
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.smtp_from, [to_email], msg.as_string())
            logger.info("Email sent to %s", to_email)
            return True
        except Exception as e:
            logger.error("Email failed: %s", e)
            return False

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        phone = phone.strip().replace(" ", "").replace("-", "")
        if phone.startswith("00"):
            phone = "+" + phone[2:]
        return phone


# Singleton
alerts = AlertService()
