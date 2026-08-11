"""
Solar Manager Online - Database Layer
Multi-tenant (location-based) + Shared Stock
"""
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

try:
    from config import Config
    DEFAULT_DB = Config.DATABASE_PATH
except Exception:
    DEFAULT_DB = str(Path(__file__).parent.parent / "data" / "solar_manager.db")

LOCATIONS = {
    "sa_main": {
        "name": "SA SOLAR & ELECTRIC CO.",
        "addr1": "MOR EMINABAAD IN FRONT OF GUJRANWALA EXPRESSWAY",
        "addr2": "GUJRANWALA, PUNJAB Pakistan",
        "phone": "03107319742",
        "email": "sasolarandelectricco@gmail.com",
        "bank_name": "MEEZAN BANK LTD",
        "bank_iban": "PK21MEZN0009020109894766",
        "bank_title": "DAWOOD",
        "bank_account": "09020109894766",
        "logo": "logo.png",
    },
    "sa_mumtaz": {
        "name": "SA SOLAR & ELECTRIC CO.",
        "addr1": "MUMTAZ MARKET OPPOSITE CHAESUP",
        "addr2": "Pakistan",
        "phone": "03107319742",
        "email": "sasolarandelectricco@gmail.com",
        "bank_name": "MEEZAN BANK LTD",
        "bank_iban": "PK21MEZN0009020109894766",
        "bank_title": "DAWOOD",
        "bank_account": "09020109894766",
        "logo": "logo.png",
    },
    "ua_kamoke": {
        "name": "UA SOLAR & ELECTRIC",
        "addr1": "OPPOSITE TO RISEN MALL",
        "addr2": "PAK-TOWN KAMOKE",
        "phone": "03107319742",
        "email": "sasolarandelectricco@gmail.com",
        "bank_name": "BANK ALFALAH ISLAMIC",
        "bank_iban": "PK44ALFH5911005002437073",
        "bank_title": "UA SOLAR & ELECTRIC",
        "bank_account": "59115002437073",
        "logo": "ua_logo.png",
    },
}

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _row_to_dict(row):
    """Safely convert sqlite3.Row / tuple / dict to a plain dict."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        return None


def _rows_to_dicts(rows):
    """Convert a list of rows to list of dicts."""
    result = []
    for r in rows or []:
        d = _row_to_dict(r)
        if d is not None:
            result.append(d)
    return result


class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or DEFAULT_DB
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._ensure_db()
        except Exception as e:
            # Never block app start — log and retry on first use
            print("DB INIT WARNING:", e)

    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_db(self):
        conn = self._conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'employee',
                location TEXT,
                created_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                category TEXT DEFAULT 'General',
                quantity REAL DEFAULT 0,
                unit TEXT DEFAULT 'pcs',
                min_stock REAL DEFAULT 5,
                purchase_price REAL DEFAULT 0,
                sale_price REAL DEFAULT 0,
                notes TEXT,
                updated_at TEXT
            )
        """)

        
        try:
            cur.execute("ALTER TABLE inventory ADD COLUMN added_at_location TEXT")
        except Exception:
            pass

        tables = [
            ("customers", """
                name TEXT NOT NULL, phone TEXT, email TEXT, address TEXT,
                project_status TEXT DEFAULT 'Lead', notes TEXT,
                created_at TEXT, updated_at TEXT
            """),
            ("expenses", """
                date TEXT NOT NULL, category TEXT DEFAULT 'General',
                amount REAL NOT NULL, description TEXT, created_at TEXT
            """),
            ("employees", """
                name TEXT NOT NULL, phone TEXT, role TEXT DEFAULT 'Staff',
                monthly_salary REAL DEFAULT 0, joining_date TEXT,
                status TEXT DEFAULT 'Active', notes TEXT,
                created_at TEXT, updated_at TEXT
            """),
            ("invoices", """
                invoice_no TEXT NOT NULL, customer_id INTEGER,
                customer_name TEXT, customer_phone TEXT, customer_address TEXT,
                date TEXT NOT NULL, subtotal REAL DEFAULT 0, discount REAL DEFAULT 0,
                total REAL DEFAULT 0, amount_paid REAL DEFAULT 0,
                payment_status TEXT DEFAULT 'Unpaid', notes TEXT,
                status TEXT DEFAULT 'Final', created_at TEXT
            """),
            ("invoice_items", """
                invoice_id INTEGER NOT NULL, item_name TEXT NOT NULL,
                quantity REAL NOT NULL, unit TEXT DEFAULT 'pcs',
                unit_price REAL NOT NULL, line_total REAL NOT NULL
            """),
            ("quotations", """
                quote_no TEXT NOT NULL, customer_id INTEGER,
                customer_name TEXT, customer_phone TEXT, customer_address TEXT,
                date TEXT NOT NULL, subtotal REAL DEFAULT 0, discount REAL DEFAULT 0,
                total REAL DEFAULT 0, notes TEXT, status TEXT DEFAULT 'Draft', created_at TEXT
            """),
            ("quotation_items", """
                quotation_id INTEGER NOT NULL, item_name TEXT NOT NULL,
                quantity REAL NOT NULL, unit TEXT DEFAULT 'pcs',
                unit_price REAL NOT NULL, line_total REAL NOT NULL
            """),
            ("dues", """
                customer_id INTEGER, customer_name TEXT NOT NULL,
                invoice_id INTEGER, invoice_no TEXT,
                total_amount REAL NOT NULL, paid_amount REAL DEFAULT 0,
                due_date TEXT, status TEXT DEFAULT 'Pending', notes TEXT,
                created_at TEXT, updated_at TEXT
            """),
            ("vendors", """
                name TEXT NOT NULL, phone TEXT, address TEXT, notes TEXT,
                created_at TEXT, updated_at TEXT
            """),
            ("vendor_orders", """
                vendor_id INTEGER, vendor_name TEXT, item_name TEXT NOT NULL,
                quantity REAL NOT NULL, unit TEXT DEFAULT 'pcs',
                unit_price REAL DEFAULT 0, total REAL DEFAULT 0,
                status TEXT DEFAULT 'Pending', order_date TEXT, received_date TEXT,
                notes TEXT, created_at TEXT
            """),
            ("customer_visits", """
                customer_name TEXT NOT NULL, phone TEXT, visit_date TEXT NOT NULL,
                notes TEXT, reminder_date TEXT, reminder_done INTEGER DEFAULT 0, created_at TEXT
            """),
            ("shopkeepers", """
                name TEXT NOT NULL, phone TEXT, address TEXT, notes TEXT,
                created_at TEXT, updated_at TEXT
            """),
            ("shopkeeper_ledger", """
                shopkeeper_id INTEGER, customer_name TEXT NOT NULL, date TEXT NOT NULL,
                description TEXT, debit REAL DEFAULT 0, credit REAL DEFAULT 0,
                notes TEXT, created_at TEXT
            """),
            ("login_logs", """
                user_id INTEGER, username TEXT, login_at TEXT, ip TEXT
            """),
        ]
        for table, extra in tables:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location TEXT NOT NULL DEFAULT 'sa_main',
                    {extra}
                )
            """)

        # Seed users (your real credentials)
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            users = [
                ("owner", _hash("Owner@SA2026"), "Owner", "owner", None),
                ("ZAKWANMAIN-44", _hash("MAINSHOPMIN"), "SA Main Employee", "employee", "sa_main"),
                ("FARHANSA-44", _hash("SASOLARMIN"), "SA Mumtaz Employee", "employee", "sa_mumtaz"),
                ("SAMEERSHAHID-44", _hash("UASOLARMIN"), "UA Employee", "employee", "ua_kamoke"),
            ]
            for u in users:
                cur.execute(
                    "INSERT INTO users (username, password_hash, full_name, role, location, created_at) VALUES (?,?,?,?,?,?)",
                    (*u, now)
                )

        cur.execute("SELECT COUNT(*) FROM inventory")
        if cur.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            items = [
                ("Solar Panel 550W Mono", "Panels", 24, "pcs", 5, 18500, 22000),
                ("Hybrid Inverter 5kW", "Inverters", 6, "pcs", 2, 95000, 115000),
                ("Battery 12V 200Ah", "Batteries", 3, "pcs", 4, 42000, 48000),
                ("DC Cable 6mm", "Cables", 120, "mtr", 50, 180, 250),
                ("MCB 63A", "Protection", 2, "pcs", 5, 1200, 1800),
            ]
            for it in items:
                cur.execute(
                    """INSERT INTO inventory (item_name, category, quantity, unit, min_stock, purchase_price, sale_price, updated_at)
                       VALUES (?,?,?,?,?,?,?,?)""", (*it, now)
                )

        conn.commit()
        conn.close()

    def authenticate(self, username, password):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username.strip(),))
        row = cur.fetchone()
        conn.close()
        if row:
            d = _row_to_dict(row)
            if d and d.get("password_hash") == _hash(password):
                return d
        return None

    def log_login(self, user, ip=""):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO login_logs (user_id, username, login_at, ip) VALUES (?,?,?,?)",
            (user["id"], user["username"], datetime.now().isoformat(), ip)
        )
        conn.commit()
        conn.close()

    def get_user(self, user_id):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return _row_to_dict(row)

    def get_inventory(self, search=""):
        """Always returns a list of plain dicts with quantity, purchase_price, sale_price."""
        conn = self._conn()
        cur = conn.cursor()
        try:
            # Prefer full select; fall back if column missing on older DB
            cols_sql = ("id, item_name, category, quantity, unit, min_stock, "
                        "purchase_price, sale_price, notes, updated_at, "
                        "COALESCE(added_at_location,'') as added_at_location")
            try:
                if search:
                    cur.execute(
                        f"SELECT {cols_sql} FROM inventory "
                        "WHERE item_name LIKE ? OR category LIKE ? ORDER BY item_name",
                        (f"%{search}%", f"%{search}%"),
                    )
                else:
                    cur.execute(f"SELECT {cols_sql} FROM inventory ORDER BY item_name")
            except Exception:
                if search:
                    cur.execute(
                        "SELECT id, item_name, category, quantity, unit, min_stock, "
                        "purchase_price, sale_price, notes, updated_at FROM inventory "
                        "WHERE item_name LIKE ? OR category LIKE ? ORDER BY item_name",
                        (f"%{search}%", f"%{search}%"),
                    )
                else:
                    cur.execute(
                        "SELECT id, item_name, category, quantity, unit, min_stock, "
                        "purchase_price, sale_price, notes, updated_at FROM inventory "
                        "ORDER BY item_name"
                    )
            cols = [d[0] for d in cur.description]
            out = []
            for row in cur.fetchall():
                if isinstance(row, dict):
                    d = {k: row.get(k) for k in cols}
                else:
                    d = dict(zip(cols, row))
                # normalize types
                d["id"] = int(d.get("id") or 0)
                d["item_name"] = str(d.get("item_name") or "")
                d["category"] = str(d.get("category") or "General")
                d["quantity"] = float(d.get("quantity") or 0)
                d["unit"] = str(d.get("unit") or "pcs")
                d["min_stock"] = float(d.get("min_stock") or 5)
                d["purchase_price"] = float(d.get("purchase_price") or 0)
                d["sale_price"] = float(d.get("sale_price") or 0)
                d["notes"] = str(d.get("notes") or "")
                d["added_at_location"] = str(d.get("added_at_location") or "")
                out.append(d)
            return out
        finally:
            conn.close()

    def add_inventory(self, item_name, category="General", quantity=0, unit="pcs", min_stock=5,
                      purchase_price=0, sale_price=0, notes="", added_at_location=""):
        conn = self._conn()
        cur = conn.cursor()
        now = datetime.now().isoformat()
        try:
            cur.execute(
                """INSERT INTO inventory (item_name, category, quantity, unit, min_stock, purchase_price, sale_price, notes, updated_at, added_at_location)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (item_name, category, quantity, unit, min_stock, purchase_price, sale_price, notes, now, added_at_location or "")
            )
        except Exception:
            cur.execute(
                """INSERT INTO inventory (item_name, category, quantity, unit, min_stock, purchase_price, sale_price, notes, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (item_name, category, quantity, unit, min_stock, purchase_price, sale_price, notes, now)
            )
        conn.commit()
        iid = cur.lastrowid
        conn.close()
        return iid

    def update_inventory(self, iid, **kwargs):
        conn = self._conn()
        cur = conn.cursor()
        fields, vals = [], []
        for k, v in kwargs.items():
            if k in ("item_name", "category", "quantity", "unit", "min_stock", "purchase_price", "sale_price", "notes"):
                fields.append(f"{k}=?")
                vals.append(v)
        if fields:
            fields.append("updated_at=?")
            vals.append(datetime.now().isoformat())
            vals.append(iid)
            cur.execute(f"UPDATE inventory SET {', '.join(fields)} WHERE id=?", vals)
            conn.commit()
        conn.close()

    def delete_inventory(self, iid):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory WHERE id=?", (iid,))
        conn.commit()
        conn.close()

    def low_stock_items(self):
        conn = self._conn()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT id, item_name, category, quantity, unit, min_stock, purchase_price, sale_price, notes "
                "FROM inventory WHERE quantity <= min_stock ORDER BY quantity"
            )
            cols = [d[0] for d in cur.description]
            rows = []
            for row in cur.fetchall():
                if isinstance(row, dict):
                    d = dict(row)
                else:
                    d = dict(zip(cols, row))
                rows.append(d)
            return rows
        finally:
            conn.close()

    def get_customers(self, location, search=""):
        conn = self._conn()
        cur = conn.cursor()
        if search:
            cur.execute(
                "SELECT * FROM customers WHERE location=? AND (name LIKE ? OR phone LIKE ?) ORDER BY name",
                (location, f"%{search}%", f"%{search}%")
            )
        else:
            cur.execute("SELECT * FROM customers WHERE location=? ORDER BY name", (location,))
        rows = _rows_to_dicts(cur.fetchall())
        conn.close()
        return rows

    def add_customer(self, location, name, phone="", email="", address="", project_status="Lead", notes=""):
        conn = self._conn()
        cur = conn.cursor()
        now = datetime.now().isoformat()
        cur.execute(
            """INSERT INTO customers (location, name, phone, email, address, project_status, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (location, name, phone, email, address, project_status, notes, now, now)
        )
        conn.commit()
        cid = cur.lastrowid
        conn.close()
        return cid

    def delete_customer(self, cid, location):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM customers WHERE id=? AND location=?", (cid, location))
        conn.commit()
        conn.close()

    def customer_count(self, location=None):
        conn = self._conn()
        cur = conn.cursor()
        if location:
            cur.execute("SELECT COUNT(*) FROM customers WHERE location=?", (location,))
        else:
            cur.execute("SELECT COUNT(*) FROM customers")
        n = cur.fetchone()[0]
        conn.close()
        return n

    def get_expenses(self, location, limit=100):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM expenses WHERE location=? ORDER BY date DESC, id DESC LIMIT ?", (location, limit))
        rows = _rows_to_dicts(cur.fetchall())
        conn.close()
        return rows

    def add_expense(self, location, date, category, amount, description=""):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO expenses (location, date, category, amount, description, created_at) VALUES (?,?,?,?,?,?)",
            (location, date, category, amount, description, datetime.now().isoformat())
        )
        conn.commit()
        eid = cur.lastrowid
        conn.close()
        return eid

    def delete_expense(self, eid, location):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM expenses WHERE id=? AND location=?", (eid, location))
        conn.commit()
        conn.close()

    def month_expenses_total(self, location=None, year_month=None):
        if not year_month:
            year_month = datetime.now().strftime("%Y-%m")
        conn = self._conn()
        cur = conn.cursor()
        if location:
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE location=? AND date LIKE ?",
                        (location, f"{year_month}%"))
        else:
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE date LIKE ?", (f"{year_month}%",))
        total = cur.fetchone()[0]
        conn.close()
        return total

    def month_sales_total(self, location=None, year_month=None):
        if not year_month:
            year_month = datetime.now().strftime("%Y-%m")
        conn = self._conn()
        cur = conn.cursor()
        if location:
            cur.execute("SELECT COALESCE(SUM(total),0) FROM invoices WHERE location=? AND date LIKE ?",
                        (location, f"{year_month}%"))
        else:
            cur.execute("SELECT COALESCE(SUM(total),0) FROM invoices WHERE date LIKE ?", (f"{year_month}%",))
        total = cur.fetchone()[0]
        conn.close()
        return total

    def pending_dues_total(self, location=None):
        conn = self._conn()
        cur = conn.cursor()
        if location:
            cur.execute("SELECT COALESCE(SUM(total_amount - paid_amount),0) FROM dues WHERE location=? AND status != 'Paid'",
                        (location,))
        else:
            cur.execute("SELECT COALESCE(SUM(total_amount - paid_amount),0) FROM dues WHERE status != 'Paid'")
        total = cur.fetchone()[0]
        conn.close()
        return total

    def employee_count(self, location=None):
        conn = self._conn()
        cur = conn.cursor()
        if location:
            cur.execute("SELECT COUNT(*) FROM employees WHERE location=? AND status='Active'", (location,))
        else:
            cur.execute("SELECT COUNT(*) FROM employees WHERE status='Active'")
        n = cur.fetchone()[0]
        conn.close()
        return n

    def get_location_info(self, location):
        return LOCATIONS.get(location, LOCATIONS["sa_main"])

    # ---------- INVOICES ----------
    def next_invoice_no(self, location):
        conn = self._conn()
        cur = conn.cursor()
        prefix = {"sa_main": "INV", "sa_mumtaz": "INVM", "ua_kamoke": "INVU"}.get(location, "INV")
        cur.execute("SELECT invoice_no FROM invoices WHERE location=? ORDER BY id DESC LIMIT 1", (location,))
        row = cur.fetchone()
        conn.close()
        if row:
            try:
                num = int("".join(c for c in row["invoice_no"] if c.isdigit()) or "0") + 1
            except Exception:
                num = 1
        else:
            num = 1001
        return f"{prefix}-{num}"

    def get_invoices(self, location, search=""):
        conn = self._conn()
        cur = conn.cursor()
        if search:
            cur.execute(
                "SELECT * FROM invoices WHERE location=? AND (invoice_no LIKE ? OR customer_name LIKE ?) ORDER BY date DESC, id DESC",
                (location, f"%{search}%", f"%{search}%")
            )
        else:
            cur.execute("SELECT * FROM invoices WHERE location=? ORDER BY date DESC, id DESC", (location,))
        rows = _rows_to_dicts(cur.fetchall())
        conn.close()
        return rows

    def get_invoice(self, iid, location):
        conn = self._conn()
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM invoices WHERE id=? AND location=?", (iid, location))
            row = cur.fetchone()
            if not row:
                return None
            inv = _row_to_dict(row) or {}
            cur.execute(
                "SELECT id, invoice_id, item_name, quantity, unit, unit_price, line_total "
                "FROM invoice_items WHERE invoice_id=? ORDER BY id",
                (iid,)
            )
            cols = [d[0] for d in cur.description]
            items = []
            for r in cur.fetchall():
                if isinstance(r, dict):
                    items.append(dict(r))
                else:
                    items.append(dict(zip(cols, r)))
            inv["items"] = items
            inv["line_items"] = items  # alias to avoid any .items method clash
            return inv
        finally:
            conn.close()

    def add_invoice(self, location, customer_name, customer_phone="", customer_address="",
                    date=None, items=None, discount=0, notes="", amount_paid=0, customer_id=None):
        conn = self._conn()
        cur = conn.cursor()
        date = date or datetime.now().strftime("%Y-%m-%d")
        inv_no = self.next_invoice_no(location)
        items = items or []
        subtotal = sum(float(i.get("line_total", 0)) for i in items)
        total = max(0, subtotal - float(discount or 0))
        paid = float(amount_paid or 0)
        if paid >= total and total > 0:
            status = "Paid"
        elif paid > 0:
            status = "Partial"
        else:
            status = "Unpaid"
        now = datetime.now().isoformat()
        cur.execute(
            """INSERT INTO invoices (location, invoice_no, customer_id, customer_name, customer_phone,
               customer_address, date, subtotal, discount, total, amount_paid, payment_status, notes, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (location, inv_no, customer_id, customer_name, customer_phone, customer_address,
             date, subtotal, discount, total, paid, status, notes, "Final", now)
        )
        iid = cur.lastrowid
        for it in items:
            cur.execute(
                """INSERT INTO invoice_items (location, invoice_id, item_name, quantity, unit, unit_price, line_total)
                   VALUES (?,?,?,?,?,?,?)""",
                (location, iid, it["item_name"], it["quantity"], it.get("unit", "pcs"),
                 it["unit_price"], it["line_total"])
            )
            # Reduce shared stock on invoice
            try:
                cur.execute("SELECT id, quantity FROM inventory WHERE item_name=?", (it["item_name"],))
                er = cur.fetchone()
                if er:
                    eid = er["id"] if not isinstance(er, tuple) else er[0]
                    eq = float(er["quantity"] if not isinstance(er, tuple) else er[1])
                    cur.execute(
                        "UPDATE inventory SET quantity=?, updated_at=? WHERE id=?",
                        (max(0, eq - float(it.get("quantity") or 0)), datetime.now().isoformat(), eid),
                    )
            except Exception:
                pass
        # Auto create due if not fully paid
        if paid < total:
            cur.execute(
                """INSERT INTO dues (location, customer_id, customer_name, invoice_id, invoice_no,
                   total_amount, paid_amount, due_date, status, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (location, customer_id, customer_name, iid, inv_no, total, paid, date, status, now, now)
            )
        conn.commit()
        conn.close()
        return iid, inv_no

    def delete_invoice(self, iid, location):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM invoice_items WHERE invoice_id=?", (iid,))
        cur.execute("DELETE FROM invoices WHERE id=? AND location=?", (iid, location))
        cur.execute("DELETE FROM dues WHERE invoice_id=? AND location=?", (iid, location))
        conn.commit()
        conn.close()

    def record_invoice_payment(self, iid, location, amount):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM invoices WHERE id=? AND location=?", (iid, location))
        inv = cur.fetchone()
        if not inv:
            conn.close()
            return False
        new_paid = float(inv["amount_paid"] or 0) + float(amount)
        total = float(inv["total"] or 0)
        if new_paid >= total:
            status = "Paid"
            new_paid = total
        elif new_paid > 0:
            status = "Partial"
        else:
            status = "Unpaid"
        cur.execute("UPDATE invoices SET amount_paid=?, payment_status=? WHERE id=?", (new_paid, status, iid))
        cur.execute("UPDATE dues SET paid_amount=?, status=?, updated_at=? WHERE invoice_id=? AND location=?",
                    (new_paid, status, datetime.now().isoformat(), iid, location))
        conn.commit()
        conn.close()
        return True

    # ---------- QUOTATIONS ----------
    def next_quote_no(self, location):
        conn = self._conn()
        cur = conn.cursor()
        prefix = {"sa_main": "QUO", "sa_mumtaz": "QUOM", "ua_kamoke": "QUOU"}.get(location, "QUO")
        cur.execute("SELECT quote_no FROM quotations WHERE location=? ORDER BY id DESC LIMIT 1", (location,))
        row = cur.fetchone()
        conn.close()
        if row:
            try:
                num = int("".join(c for c in row["quote_no"] if c.isdigit()) or "0") + 1
            except Exception:
                num = 1
        else:
            num = 501
        return f"{prefix}-{num}"

    def get_quotations(self, location, search=""):
        conn = self._conn()
        cur = conn.cursor()
        if search:
            cur.execute(
                "SELECT * FROM quotations WHERE location=? AND (quote_no LIKE ? OR customer_name LIKE ?) ORDER BY date DESC, id DESC",
                (location, f"%{search}%", f"%{search}%")
            )
        else:
            cur.execute("SELECT * FROM quotations WHERE location=? ORDER BY date DESC, id DESC", (location,))
        rows = _rows_to_dicts(cur.fetchall())
        conn.close()
        return rows

    def get_quotation(self, qid, location):
        conn = self._conn()
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM quotations WHERE id=? AND location=?", (qid, location))
            row = cur.fetchone()
            if not row:
                return None
            q = _row_to_dict(row) or {}
            cur.execute(
                "SELECT id, quotation_id, item_name, quantity, unit, unit_price, line_total "
                "FROM quotation_items WHERE quotation_id=? ORDER BY id",
                (qid,)
            )
            cols = [d[0] for d in cur.description]
            items = []
            for r in cur.fetchall():
                if isinstance(r, dict):
                    items.append(dict(r))
                else:
                    items.append(dict(zip(cols, r)))
            q["items"] = items
            q["line_items"] = items
            return q
        finally:
            conn.close()

    def add_quotation(self, location, customer_name, customer_phone="", customer_address="",
                      date=None, items=None, discount=0, notes="", customer_id=None):
        conn = self._conn()
        cur = conn.cursor()
        date = date or datetime.now().strftime("%Y-%m-%d")
        qno = self.next_quote_no(location)
        items = items or []
        subtotal = sum(float(i.get("line_total", 0)) for i in items)
        total = max(0, subtotal - float(discount or 0))
        now = datetime.now().isoformat()
        cur.execute(
            """INSERT INTO quotations (location, quote_no, customer_id, customer_name, customer_phone,
               customer_address, date, subtotal, discount, total, notes, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (location, qno, customer_id, customer_name, customer_phone, customer_address,
             date, subtotal, discount, total, notes, "Draft", now)
        )
        qid = cur.lastrowid
        for it in items:
            cur.execute(
                """INSERT INTO quotation_items (location, quotation_id, item_name, quantity, unit, unit_price, line_total)
                   VALUES (?,?,?,?,?,?,?)""",
                (location, qid, it["item_name"], it["quantity"], it.get("unit", "pcs"),
                 it["unit_price"], it["line_total"])
            )
        conn.commit()
        conn.close()
        return qid, qno


    def convert_quotation_to_invoice(self, qid, location):
        """Convert quotation to invoice and reduce stock. Returns (invoice_id, invoice_no) or None."""
        q = self.get_quotation(qid, location)
        if not q:
            return None
        items = []
        for it in (q.get("items") or []):
            items.append({
                "item_name": it.get("item_name"),
                "quantity": float(it.get("quantity") or 0),
                "unit": it.get("unit") or "pcs",
                "unit_price": float(it.get("unit_price") or 0),
                "line_total": float(it.get("line_total") or 0),
            })
        iid, inv_no = self.add_invoice(
            location,
            q.get("customer_name") or "",
            customer_phone=q.get("customer_phone") or "",
            customer_address=q.get("customer_address") or "",
            date=None,
            items=items,
            discount=float(q.get("discount") or 0),
            notes=(q.get("notes") or "") + f" (from {q.get('quote_no')})",
            amount_paid=0,
        )
        # mark quotation converted
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE quotations SET status=? WHERE id=? AND location=?",
            ("Converted", qid, location),
        )
        conn.commit()
        conn.close()
        return iid, inv_no

    def delete_quotation(self, qid, location):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM quotation_items WHERE quotation_id=?", (qid,))
        cur.execute("DELETE FROM quotations WHERE id=? AND location=?", (qid, location))
        conn.commit()
        conn.close()

    # ---------- DUES ----------
    def get_dues(self, location, status_filter=""):
        conn = self._conn()
        cur = conn.cursor()
        if status_filter:
            cur.execute("SELECT * FROM dues WHERE location=? AND status=? ORDER BY due_date", (location, status_filter))
        else:
            cur.execute("SELECT * FROM dues WHERE location=? ORDER BY due_date", (location,))
        rows = _rows_to_dicts(cur.fetchall())
        conn.close()
        return rows

    def add_due(self, location, customer_name, total_amount, paid_amount=0, due_date="", notes="",
                invoice_id=None, invoice_no="", customer_id=None):
        conn = self._conn()
        cur = conn.cursor()
        now = datetime.now().isoformat()
        status = "Paid" if float(paid_amount) >= float(total_amount) else ("Partial" if float(paid_amount) > 0 else "Pending")
        cur.execute(
            """INSERT INTO dues (location, customer_id, customer_name, invoice_id, invoice_no,
               total_amount, paid_amount, due_date, status, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (location, customer_id, customer_name, invoice_id, invoice_no,
             total_amount, paid_amount, due_date or datetime.now().strftime("%Y-%m-%d"),
             status, notes, now, now)
        )
        did = cur.lastrowid
        conn.commit()
        conn.close()
        return did

    def record_due_payment(self, did, location, amount):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM dues WHERE id=? AND location=?", (did, location))
        d = cur.fetchone()
        if not d:
            conn.close()
            return False
        new_paid = float(d["paid_amount"] or 0) + float(amount)
        total = float(d["total_amount"] or 0)
        status = "Paid" if new_paid >= total else ("Partial" if new_paid > 0 else "Pending")
        if new_paid > total:
            new_paid = total
        cur.execute("UPDATE dues SET paid_amount=?, status=?, updated_at=? WHERE id=?",
                    (new_paid, status, datetime.now().isoformat(), did))
        if d["invoice_id"]:
            cur.execute("UPDATE invoices SET amount_paid=?, payment_status=? WHERE id=?",
                        (new_paid, status, d["invoice_id"]))
        conn.commit()
        conn.close()
        return True

    def delete_due(self, did, location):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM dues WHERE id=? AND location=?", (did, location))
        conn.commit()
        conn.close()

    # ---------- EMPLOYEES ----------
    def get_employees(self, location, search=""):
        conn = self._conn()
        cur = conn.cursor()
        if search:
            cur.execute("SELECT * FROM employees WHERE location=? AND (name LIKE ? OR phone LIKE ?) ORDER BY name",
                        (location, f"%{search}%", f"%{search}%"))
        else:
            cur.execute("SELECT * FROM employees WHERE location=? ORDER BY name", (location,))
        rows = _rows_to_dicts(cur.fetchall())
        conn.close()
        return rows

    def add_employee(self, location, name, phone="", role="Staff", monthly_salary=0, joining_date="", status="Active", notes=""):
        conn = self._conn()
        cur = conn.cursor()
        now = datetime.now().isoformat()
        cur.execute(
            """INSERT INTO employees (location, name, phone, role, monthly_salary, joining_date, status, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (location, name, phone, role, monthly_salary, joining_date or None, status, notes, now, now)
        )
        eid = cur.lastrowid
        conn.commit()
        conn.close()
        return eid

    def delete_employee(self, eid, location):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM employees WHERE id=? AND location=?", (eid, location))
        conn.commit()
        conn.close()

    # ---------- VENDORS ----------
    def get_vendors(self, location, search=""):
        conn = self._conn()
        cur = conn.cursor()
        if search:
            cur.execute("SELECT * FROM vendors WHERE location=? AND name LIKE ? ORDER BY name", (location, f"%{search}%"))
        else:
            cur.execute("SELECT * FROM vendors WHERE location=? ORDER BY name", (location,))
        rows = _rows_to_dicts(cur.fetchall())
        conn.close()
        return rows

    def add_vendor(self, location, name, phone="", address="", notes=""):
        conn = self._conn()
        cur = conn.cursor()
        now = datetime.now().isoformat()
        cur.execute(
            "INSERT INTO vendors (location, name, phone, address, notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (location, name, phone, address, notes, now, now)
        )
        vid = cur.lastrowid
        conn.commit()
        conn.close()
        return vid

    def delete_vendor(self, vid, location):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM vendors WHERE id=? AND location=?", (vid, location))
        conn.commit()
        conn.close()

    def get_vendor_orders(self, location):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM vendor_orders WHERE location=? ORDER BY order_date DESC, id DESC", (location,))
        rows = _rows_to_dicts(cur.fetchall())
        conn.close()
        return rows

    def add_vendor_order(self, location, vendor_name, item_name, quantity, unit="pcs", unit_price=0, notes="", vendor_id=None):
        conn = self._conn()
        cur = conn.cursor()
        now = datetime.now().isoformat()
        total = float(quantity) * float(unit_price)
        cur.execute(
            """INSERT INTO vendor_orders (location, vendor_id, vendor_name, item_name, quantity, unit, unit_price, total,
               status, order_date, notes, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (location, vendor_id, vendor_name, item_name, quantity, unit, unit_price, total,
             "Pending", datetime.now().strftime("%Y-%m-%d"), notes, now)
        )
        oid = cur.lastrowid
        # Auto-receive: immediately add to shared stock
        cur.execute("UPDATE vendor_orders SET status=?, received_date=? WHERE id=?",
                    ("Received", datetime.now().strftime("%Y-%m-%d"), oid))
        cur.execute("SELECT id, quantity FROM inventory WHERE item_name=?", (item_name,))
        existing = cur.fetchone()
        if existing:
            eid = existing["id"] if not isinstance(existing, tuple) else existing[0]
            cur.execute(
                "UPDATE inventory SET quantity=quantity+?, purchase_price=?, updated_at=? WHERE id=?",
                (float(quantity), float(unit_price or 0), now, eid),
            )
        else:
            sale = float(unit_price or 0) * 1.2
            cur.execute(
                """INSERT INTO inventory (item_name, category, quantity, unit, min_stock, purchase_price, sale_price, updated_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (item_name, "General", float(quantity), unit, 5, float(unit_price or 0), sale, now),
            )
        conn.commit()
        conn.close()
        return oid

    def receive_vendor_order(self, oid, location):
        """Mark received and add to shared stock."""
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM vendor_orders WHERE id=? AND location=?", (oid, location))
        o = cur.fetchone()
        if not o:
            conn.close()
            return False
        o = dict(o)
        cur.execute("UPDATE vendor_orders SET status=?, received_date=? WHERE id=?",
                    ("Received", datetime.now().strftime("%Y-%m-%d"), oid))
        # Add to shared inventory
        cur.execute("SELECT id, quantity FROM inventory WHERE item_name=?", (o["item_name"],))
        existing = cur.fetchone()
        now = datetime.now().isoformat()
        if existing:
            cur.execute("UPDATE inventory SET quantity=quantity+?, purchase_price=?, updated_at=? WHERE id=?",
                        (o["quantity"], o["unit_price"], now, existing["id"]))
        else:
            cur.execute(
                """INSERT INTO inventory (item_name, category, quantity, unit, min_stock, purchase_price, sale_price, updated_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (o["item_name"], "General", o["quantity"], o["unit"], 5, o["unit_price"], o["unit_price"] * 1.2, now)
            )
        conn.commit()
        conn.close()
        return True


    def reduce_stock(self, item_name, qty):
        """Reduce shared inventory quantity (for invoices). Returns True if updated."""
        conn = self._conn()
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, quantity FROM inventory WHERE item_name=?", (item_name,))
            row = cur.fetchone()
            if not row:
                return False
            rid = row["id"] if not isinstance(row, tuple) else row[0]
            q = float(row["quantity"] if not isinstance(row, tuple) else row[1])
            new_q = max(0, q - float(qty or 0))
            cur.execute(
                "UPDATE inventory SET quantity=?, updated_at=? WHERE id=?",
                (new_q, datetime.now().isoformat(), rid),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def get_sale_price(self, item_name):
        conn = self._conn()
        cur = conn.cursor()
        try:
            cur.execute("SELECT sale_price FROM inventory WHERE item_name=?", (item_name,))
            row = cur.fetchone()
            if not row:
                return 0
            return float(row["sale_price"] if not isinstance(row, tuple) else row[0] or 0)
        finally:
            conn.close()

    # ---------- VISITS ----------
    def get_visits(self, location):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM customer_visits WHERE location=? ORDER BY visit_date DESC", (location,))
        rows = _rows_to_dicts(cur.fetchall())
        conn.close()
        return rows

    def add_visit(self, location, customer_name, phone="", visit_date=None, notes=""):
        conn = self._conn()
        cur = conn.cursor()
        visit_date = visit_date or datetime.now().strftime("%Y-%m-%d")
        from datetime import timedelta
        rem = (datetime.strptime(visit_date, "%Y-%m-%d") + timedelta(days=3)).strftime("%Y-%m-%d")
        cur.execute(
            """INSERT INTO customer_visits (location, customer_name, phone, visit_date, notes, reminder_date, reminder_done, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (location, customer_name, phone, visit_date, notes, rem, 0, datetime.now().isoformat())
        )
        vid = cur.lastrowid
        conn.commit()
        conn.close()
        return vid

    def delete_visit(self, vid, location):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM customer_visits WHERE id=? AND location=?", (vid, location))
        conn.commit()
        conn.close()

    # ---------- SHOPKEEPERS ----------
    def get_shopkeepers(self, location):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM shopkeepers WHERE location=? ORDER BY name", (location,))
        rows = _rows_to_dicts(cur.fetchall())
        conn.close()
        return rows

    def add_shopkeeper(self, location, name, phone="", address="", notes=""):
        conn = self._conn()
        cur = conn.cursor()
        now = datetime.now().isoformat()
        cur.execute(
            "INSERT INTO shopkeepers (location, name, phone, address, notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (location, name, phone, address, notes, now, now)
        )
        sid = cur.lastrowid
        conn.commit()
        conn.close()
        return sid

    def delete_shopkeeper(self, sid, location):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM shopkeepers WHERE id=? AND location=?", (sid, location))
        conn.commit()
        conn.close()

    def get_shopkeeper_ledger(self, location, shopkeeper_id=None):
        conn = self._conn()
        cur = conn.cursor()
        if shopkeeper_id:
            cur.execute("SELECT * FROM shopkeeper_ledger WHERE location=? AND shopkeeper_id=? ORDER BY date DESC",
                        (location, shopkeeper_id))
        else:
            cur.execute("SELECT * FROM shopkeeper_ledger WHERE location=? ORDER BY date DESC", (location,))
        rows = _rows_to_dicts(cur.fetchall())
        conn.close()
        return rows

    def add_shop_ledger_entry(self, location, customer_name, date, description="", debit=0, credit=0, notes="", shopkeeper_id=None):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO shopkeeper_ledger (location, shopkeeper_id, customer_name, date, description, debit, credit, notes, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (location, shopkeeper_id, customer_name, date, description, debit, credit, notes, datetime.now().isoformat())
        )
        lid = cur.lastrowid
        conn.commit()
        conn.close()
        return lid
