# SA Solar Manager — Full Fixed Version

Complete business management system for SA Solar & UA Solar.

## Accounts

| Role | Username | Password | Access |
|------|----------|----------|--------|
| **Owner** | owner | Owner@SA2026 | Full access to ALL locations + Profit + Settings |
| SA Main Shop | ZAKWANMAIN-44 | MAINSHOPMIN | Employee (Add/View only) |
| SA Mumtaz Market | FARHANSA-44 | SASOLARMIN | Employee (Add/View only) |
| UA Solar Kamoke | SAMEERSHAHID-44 | UASOLARMIN | Employee (Add/View only) |

## Owner features
- Switch between all 3 locations from the top dropdown
- See data of every shop
- Profit section (Owner only)
- Settings section (Owner only)
- Full Edit/Delete rights on everything
- Shared stock control

## Employee features
- Only their own location data
- Can Add and View
- Cannot Edit/Delete (except where allowed)
- No Profit, no Settings

## Modules
- Dashboard with stats + low stock alerts
- Customers
- Stock / Inventory (shared, fixed)
- Invoices (Create, View, **Print**, Excel)
- Quotations (Create, View, **Print**)
- Expenses, Dues (ledger), Employees, Vendors, Customer Visits, Shopkeepers
- Profit (Owner)
- Settings / Login alerts (Owner)

## Deploy on Railway
1. Push this entire folder to GitHub
2. Railway → New Project → Deploy from GitHub
3. Wait for deploy to finish
4. Open the public URL → Login page appears

## Local run
```bash
pip install -r requirements.txt
python run.py
```
Open http://127.0.0.1:5000
