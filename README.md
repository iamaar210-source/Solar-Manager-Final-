# Solar Manager Online

Full web version of SA Solar / UA Solar Manager for 4 accounts.

## Login Accounts

| Account | Username | Password | Role |
|---------|----------|----------|------|
| **Owner** | `owner` | `Owner@SA2026` | Full access |
| **SA Main Shop** | `ZAKWANMAIN-44` | `MAINSHOPMIN` | Employee |
| **SA Mumtaz Market** | `FARHANSA-44` | `SASOLARMIN` | Employee |
| **UA Solar Kamoke** | `SAMEERSHAHID-44` | `UASOLARMIN` | Employee |

## Run locally

```bash
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:5000

## SMS + Email Login Alerts

Alerts are sent **only when someone logs in** (to Owner phone + email).

### Without API keys (default)
Alerts are logged to `logs/alerts.log` and printed in the terminal — good for testing.

### Enable real SMS

**Option A – Twilio**
```
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+1234567890
ALERT_PHONE=03107319742
```

**Option B – Local Pakistani SMS API**
```
SMS_API_URL=https://your-provider.com/api/send?key={key}&to={phone}&message={message}
SMS_API_KEY=your_key
SMS_API_METHOD=GET
ALERT_PHONE=03107319742
```

**Email (optional, Gmail example)**
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your_app_password
ALERT_EMAIL=sasolarandelectricco@gmail.com
```

Set these as environment variables (or in Railway → Variables).

## Deploy on Railway

1. Push `solar_web` folder to GitHub
2. Railway → New Project → Deploy from GitHub
3. Add environment variables above
4. Railway uses `Procfile` automatically
5. Share the public URL with all 4 computers

## Features

- 4 separate accounts, data isolated per location
- Owner can switch locations
- Shared stock (Owner controls)
- Employees: Add + View only (no Edit/Delete)
- Login SMS + Email alerts
- Full Invoices (Create, View, Print, Excel)
- Quotations (Create, View, Print)
- Dues, Expenses, Employees, Vendors, Visits, Shopkeepers, Profit
- UA dashboard without Active Staff
- Mumtaz uses SA Solar name + Mumtaz Market address
