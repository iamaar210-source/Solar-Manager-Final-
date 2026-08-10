# SA Solar Manager Online (Fully Fixed)

Web version for SA Solar / UA Solar – 4 accounts, shared stock, invoices & quotations with print.

## Login Accounts

| Account              | Username          | Password      | Role     |
|----------------------|-------------------|---------------|----------|
| **Owner**            | owner            | Owner@SA2026  | Full access |
| SA Main Shop         | ZAKWANMAIN-44     | MAINSHOPMIN   | Employee |
| SA Mumtaz Market     | FARHANSA-44       | SASOLARMIN    | Employee |
| UA Solar Kamoke      | SAMEERSHAHID-44   | UASOLARMIN    | Employee |

## What was fixed in this package

- Inventory / Stock page no longer crashes (`tuple has no attribute quantity`)
- Invoice View + Print now robust and printable
- Quotation View + Print now robust and printable
- Login page always available at `/login` (root `/` redirects correctly)
- All database rows safely converted to dicts
- Logos included (`logo.png` + `ua_logo.png`)
- Railway / Docker ready

## Deploy on Railway

1. Create new project → Deploy from GitHub (or upload this zip)
2. If uploading zip: extract and push to a GitHub repo, then connect Railway
3. Optional environment variables (SMS / Email alerts):
   - `ALERT_PHONE=03107319742`
   - `ALERT_EMAIL=sasolarandelectricco@gmail.com`
   - Twilio or local SMS API vars (see previous README)
4. Railway will use the Dockerfile / Procfile automatically
5. After deploy open the public URL → you should see the Login page

## Run locally

```bash
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:5000

## Features

- 4 separate accounts, data isolated per location
- Owner can switch locations
- Shared stock (Owner controls)
- Employees: Add + View only
- Login SMS + Email alerts
- Full Invoices (Create, View, Print, Excel)
- Quotations (Create, View, Print)
- Dues, Expenses, Employees, Vendors, Visits, Shopkeepers, Profit
