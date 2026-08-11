from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response
from functools import wraps
from datetime import datetime
from app.database import Database, LOCATIONS
from config import Config
from app.alerts import alerts
import io

def _excel_response(filename, headers, rows):
    """Build an Excel file download response."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Export"
    ws.append(headers)
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = make_response(buf.read())
    resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return resp


bp = Blueprint("main", __name__)
db = Database()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if "user_id" not in session:
        return None
    return db.get_user(session["user_id"])

def get_active_location(user):
    if user["role"] == "owner":
        return session.get("view_location", "sa_main")
    return user["location"] or "sa_main"

def can_edit(user):
    return user and user["role"] == "owner"

def common_ctx(user):
    loc = get_active_location(user)
    return dict(
        user=user, location=loc, can_edit=can_edit(user),
        loc_info=db.get_location_info(loc), locations=LOCATIONS
    )

# ---------- AUTH ----------
@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.authenticate(username, password)
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["view_location"] = user["location"] or "sa_main"
            session["view_all"] = False
            db.log_login(user, request.remote_addr or "")
            # Send SMS + Email alert to Owner (login only)
            result = alerts.send_login_alert(
                username=user["username"],
                full_name=user.get("full_name") or user["username"],
                location=user.get("location") or "Owner",
                ip=request.remote_addr or "",
            )
            if result.get("sms") or result.get("email"):
                flash("Login successful. SMS + Email alert sent to Owner.", "info")
            else:
                flash("Login successful. (Alert logged – configure SMS/Email API for real delivery)", "info")
            return redirect(url_for("main.dashboard"))
        flash("Invalid username or password", "error")
    return render_template("login.html")

@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))

@bp.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("main.login"))
    return redirect(url_for("main.dashboard"))

@bp.route("/switch-location/<loc>")
@login_required
def switch_location(loc):
    user = get_current_user()
    if user["role"] != "owner":
        flash("Only Owner can switch locations", "error")
        return redirect(url_for("main.dashboard"))
    if loc in LOCATIONS:
        session["view_location"] = loc
        session["view_all"] = False
    return redirect(request.referrer or url_for("main.dashboard"))

# ---------- DASHBOARD ----------
@bp.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    ctx = common_ctx(user)
    loc = ctx["location"]
    stats = {
        "customers": db.customer_count(loc),
        "sales": db.month_sales_total(loc),
        "expenses": db.month_expenses_total(loc),
        "dues": db.pending_dues_total(loc),
        "staff": db.employee_count(loc),
    }
    low_stock = db.low_stock_items()
    is_ua = (loc == "ua_kamoke")
    return render_template("dashboard.html", stats=stats, low_stock=low_stock, is_ua=is_ua, **ctx)

# ---------- CUSTOMERS ----------
@bp.route("/customers")
@login_required
def customers():
    user = get_current_user()
    ctx = common_ctx(user)
    search = request.args.get("q", "")
    rows = db.get_customers(ctx["location"], search)
    return render_template("customers.html", customers=rows, search=search, **ctx)

@bp.route("/customers/add", methods=["POST"])
@login_required
def customers_add():
    user = get_current_user()
    loc = get_active_location(user)
    name = request.form.get("name", "").strip()
    if not name:
        flash("Name is required", "error")
        return redirect(url_for("main.customers"))
    db.add_customer(loc, name, phone=request.form.get("phone", ""), email=request.form.get("email", ""),
                    address=request.form.get("address", ""), project_status=request.form.get("status", "Lead"),
                    notes=request.form.get("notes", ""))
    flash("Customer added", "success")
    return redirect(url_for("main.customers"))

@bp.route("/customers/delete/<int:cid>", methods=["POST"])
@login_required
def customers_delete(cid):
    user = get_current_user()
    if not can_edit(user):
        flash("Only Owner can delete", "error")
        return redirect(url_for("main.customers"))
    db.delete_customer(cid, get_active_location(user))
    flash("Customer deleted", "success")
    return redirect(url_for("main.customers"))

# ---------- STOCK ----------
@bp.route("/stock")
@login_required
def stock():
    user = get_current_user()
    if not user:
        return redirect(url_for("main.login"))
    ctx = common_ctx(user)
    search = request.args.get("q", "") or ""
    items = []
    try:
        raw = db.get_inventory(search) or []
        for r in raw:
            try:
                if not isinstance(r, dict):
                    r = dict(r)
            except Exception:
                continue
            try:
                items.append({
                    "id": r.get("id") or 0,
                    "item_name": str(r.get("item_name") or ""),
                    "category": str(r.get("category") or "General"),
                    "quantity": float(r.get("quantity") or 0),
                    "unit": str(r.get("unit") or "pcs"),
                    "min_stock": float(r.get("min_stock") or 5),
                    "purchase_price": float(r.get("purchase_price") or 0),
                    "sale_price": float(r.get("sale_price") or 0),
                    "notes": str(r.get("notes") or ""),
                })
            except Exception:
                continue
    except Exception as e:
        import traceback
        print("STOCK FETCH ERROR:", traceback.format_exc())
        flash(f"Could not load stock list (showing empty). Detail: {e}", "error")
    return render_template("stock.html", items=items, search=search, **ctx)



@bp.route("/stock/add", methods=["POST"])
@login_required
def stock_add():
    user = get_current_user()
    if not can_edit(user):
        flash("Only Owner can add/edit stock", "error")
        return redirect(url_for("main.stock"))
    name = request.form.get("item_name", "").strip()
    if not name:
        flash("Item name required", "error")
        return redirect(url_for("main.stock"))
    db.add_inventory(item_name=name, category=request.form.get("category", "General"),
                     quantity=float(request.form.get("quantity") or 0), unit=request.form.get("unit", "pcs"),
                     min_stock=float(request.form.get("min_stock") or 5),
                     purchase_price=float(request.form.get("purchase_price") or 0),
                     sale_price=float(request.form.get("sale_price") or 0),
                     notes=request.form.get("notes", ""))
    flash("Stock added — visible in ALL accounts", "success")
    return redirect(url_for("main.stock"))

@bp.route("/stock/delete/<int:iid>", methods=["POST"])
@login_required
def stock_delete(iid):
    user = get_current_user()
    if not can_edit(user):
        flash("Only Owner can delete stock", "error")
        return redirect(url_for("main.stock"))
    db.delete_inventory(iid)
    flash("Item deleted", "success")
    return redirect(url_for("main.stock"))

# ---------- EXPENSES ----------
@bp.route("/expenses")
@login_required
def expenses():
    user = get_current_user()
    ctx = common_ctx(user)
    rows = db.get_expenses(ctx["location"])
    return render_template("expenses.html", expenses=rows, **ctx)

@bp.route("/expenses/add", methods=["POST"])
@login_required
def expenses_add():
    user = get_current_user()
    loc = get_active_location(user)
    date = request.form.get("date") or datetime.now().strftime("%Y-%m-%d")
    amount = float(request.form.get("amount") or 0)
    if amount <= 0:
        flash("Amount required", "error")
        return redirect(url_for("main.expenses"))
    db.add_expense(loc, date, request.form.get("category", "General"), amount, request.form.get("description", ""))
    flash("Expense added", "success")
    return redirect(url_for("main.expenses"))

@bp.route("/expenses/delete/<int:eid>", methods=["POST"])
@login_required
def expenses_delete(eid):
    user = get_current_user()
    if not can_edit(user):
        flash("Only Owner can delete", "error")
        return redirect(url_for("main.expenses"))
    db.delete_expense(eid, get_active_location(user))
    flash("Expense deleted", "success")
    return redirect(url_for("main.expenses"))

# ---------- INVOICES ----------
@bp.route("/invoices")
@login_required
def invoices():
    user = get_current_user()
    ctx = common_ctx(user)
    search = request.args.get("q", "")
    rows = db.get_invoices(ctx["location"], search)
    stock = db.get_inventory()
    customers = db.get_customers(ctx["location"])
    return render_template("invoices.html", invoices=rows, stock=stock, customers=customers, search=search, **ctx)

@bp.route("/invoices/add", methods=["POST"])
@login_required
def invoices_add():
    user = get_current_user()
    loc = get_active_location(user)
    try:
        customer_name = request.form.get("customer_name", "").strip()
        if not customer_name:
            flash("Customer name required", "error")
            return redirect(url_for("main.invoices"))
        names = request.form.getlist("item_name[]")
        qtys = request.form.getlist("qty[]")
        prices = request.form.getlist("price[]")
        items = []
        for n, q, p in zip(names, qtys, prices):
            if n and str(n).strip() and float(q or 0) > 0:
                qty = float(q or 0)
                price = float(p or 0)
                items.append({"item_name": str(n).strip(), "quantity": qty, "unit": "pcs",
                              "unit_price": price, "line_total": qty * price})
        if not items:
            flash("Add at least one item with quantity", "error")
            return redirect(url_for("main.invoices"))
        iid, inv_no = db.add_invoice(
            loc, customer_name,
            customer_phone=request.form.get("customer_phone", ""),
            customer_address=request.form.get("customer_address", ""),
            date=request.form.get("date") or datetime.now().strftime("%Y-%m-%d"),
            items=items,
            discount=float(request.form.get("discount") or 0),
            notes=request.form.get("notes", ""),
            amount_paid=float(request.form.get("amount_paid") or 0)
        )
        flash(f"Invoice {inv_no} created", "success")
        return redirect(url_for("main.invoice_view", iid=iid))
    except Exception as e:
        flash(f"Could not create invoice: {e}", "error")
        return redirect(url_for("main.invoices"))

@bp.route("/invoices/<int:iid>")
@login_required
def invoice_view(iid):
    try:
        user = get_current_user()
        ctx = common_ctx(user)
        inv = db.get_invoice(iid, ctx["location"])
        if not inv:
            flash("Invoice not found", "error")
            return redirect(url_for("main.invoices"))
        if "items" not in inv or inv["items"] is None:
            inv["items"] = []
        return render_template("invoice_view.html", inv=inv, **ctx)
    except Exception as e:
        import traceback
        print("INVOICE VIEW ERROR:", traceback.format_exc())
        flash(f"Invoice error: {e}", "error")
        return redirect(url_for("main.invoices"))

@bp.route("/invoices/<int:iid>/print")
@login_required
def invoice_print(iid):
    try:
        user = get_current_user()
        ctx = common_ctx(user)
        inv = db.get_invoice(iid, ctx["location"])
        if not inv:
            flash("Invoice not found", "error")
            return redirect(url_for("main.invoices"))
        if "items" not in inv or inv["items"] is None:
            inv["items"] = []
        return render_template("invoice_print.html", inv=inv, **ctx)
    except Exception as e:
        import traceback
        print("INVOICE PRINT ERROR:", traceback.format_exc())
        flash(f"Print error: {e}", "error")
        return redirect(url_for("main.invoices"))

@bp.route("/invoices/<int:iid>/pay", methods=["POST"])
@login_required
def invoice_pay(iid):
    user = get_current_user()
    loc = get_active_location(user)
    amount = float(request.form.get("amount") or 0)
    if amount > 0:
        db.record_invoice_payment(iid, loc, amount)
        flash("Payment recorded", "success")
    return redirect(url_for("main.invoice_view", iid=iid))

@bp.route("/invoices/delete/<int:iid>", methods=["POST"])
@login_required
def invoices_delete(iid):
    user = get_current_user()
    if not can_edit(user):
        flash("Only Owner can delete", "error")
        return redirect(url_for("main.invoices"))
    db.delete_invoice(iid, get_active_location(user))
    flash("Invoice deleted", "success")
    return redirect(url_for("main.invoices"))

@bp.route("/invoices/excel")
@login_required
def invoices_excel():
    user = get_current_user()
    loc = get_active_location(user)
    rows = db.get_invoices(loc)
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Invoices"
        ws.append(["Invoice No", "Customer", "Phone", "Date", "Total", "Paid", "Status"])
        for r in rows:
            ws.append([r["invoice_no"], r["customer_name"], r.get("customer_phone"), r["date"],
                       r["total"], r.get("amount_paid"), r.get("payment_status")])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        resp.headers["Content-Disposition"] = f"attachment; filename=invoices_{loc}.xlsx"
        return resp
    except Exception as e:
        flash(f"Excel export error: {e}", "error")
        return redirect(url_for("main.invoices"))

# ---------- QUOTATIONS ----------
@bp.route("/quotations")
@login_required
def quotations():
    user = get_current_user()
    ctx = common_ctx(user)
    search = request.args.get("q", "")
    rows = db.get_quotations(ctx["location"], search)
    stock = db.get_inventory()
    return render_template("quotations.html", quotations=rows, stock=stock, search=search, **ctx)

@bp.route("/quotations/add", methods=["POST"])
@login_required
def quotations_add():
    user = get_current_user()
    loc = get_active_location(user)
    try:
        customer_name = request.form.get("customer_name", "").strip()
        if not customer_name:
            flash("Customer name required", "error")
            return redirect(url_for("main.quotations"))
        names = request.form.getlist("item_name[]")
        qtys = request.form.getlist("qty[]")
        prices = request.form.getlist("price[]")
        items = []
        for n, q, pr in zip(names, qtys, prices):
            if n and str(n).strip() and float(q or 0) > 0:
                qty = float(q or 0)
                price = float(pr or 0)
                items.append({"item_name": str(n).strip(), "quantity": qty, "unit": "pcs",
                              "unit_price": price, "line_total": qty * price})
        if not items:
            flash("Add at least one item with quantity", "error")
            return redirect(url_for("main.quotations"))
        qid, qno = db.add_quotation(
            loc, customer_name,
            customer_phone=request.form.get("customer_phone", ""),
            customer_address=request.form.get("customer_address", ""),
            date=request.form.get("date") or datetime.now().strftime("%Y-%m-%d"),
            items=items, discount=float(request.form.get("discount") or 0),
            notes=request.form.get("notes", "")
        )
        if request.form.get("add_customer") == "yes":
            db.add_customer(loc, customer_name, phone=request.form.get("customer_phone", ""),
                            address=request.form.get("customer_address", ""))
        flash(f"Quotation {qno} created", "success")
        return redirect(url_for("main.quotation_view", qid=qid))
    except Exception as e:
        flash(f"Could not create quotation: {e}", "error")
        return redirect(url_for("main.quotations"))


@bp.route("/quotations/<int:qid>")
@login_required
def quotation_view(qid):
    try:
        user = get_current_user()
        ctx = common_ctx(user)
        q = db.get_quotation(qid, ctx["location"])
        if not q:
            flash("Quotation not found", "error")
            return redirect(url_for("main.quotations"))
        if "items" not in q or q["items"] is None:
            q["items"] = []
        return render_template("quotation_view.html", q=q, **ctx)
    except Exception as e:
        import traceback
        print("QUOTATION VIEW ERROR:", traceback.format_exc())
        flash(f"Quotation error: {e}", "error")
        return redirect(url_for("main.quotations"))

@bp.route("/quotations/<int:qid>/print")
@login_required
def quotation_print(qid):
    try:
        user = get_current_user()
        ctx = common_ctx(user)
        q = db.get_quotation(qid, ctx["location"])
        if not q:
            flash("Not found", "error")
            return redirect(url_for("main.quotations"))
        if "items" not in q or q["items"] is None:
            q["items"] = []
        return render_template("quotation_print.html", q=q, **ctx)
    except Exception as e:
        import traceback
        print("QUOTATION PRINT ERROR:", traceback.format_exc())
        flash(f"Print error: {e}", "error")
        return redirect(url_for("main.quotations"))


@bp.route("/quotations/<int:qid>/to-invoice", methods=["POST"])
@login_required
def quotation_to_invoice(qid):
    user = get_current_user()
    loc = get_active_location(user)
    try:
        result = db.convert_quotation_to_invoice(qid, loc)
        if not result:
            flash("Quotation not found", "error")
            return redirect(url_for("main.quotations"))
        iid, inv_no = result
        flash(f"Converted to Invoice {inv_no} — stock reduced", "success")
        return redirect(url_for("main.invoice_view", iid=iid))
    except Exception as e:
        flash(f"Convert error: {e}", "error")
        return redirect(url_for("main.quotations"))

@bp.route("/quotations/delete/<int:qid>", methods=["POST"])
@login_required
def quotations_delete(qid):
    user = get_current_user()
    if not can_edit(user):
        flash("Only Owner can delete", "error")
        return redirect(url_for("main.quotations"))
    db.delete_quotation(qid, get_active_location(user))
    flash("Quotation deleted", "success")
    return redirect(url_for("main.quotations"))

# ---------- DUES ----------
@bp.route("/dues")
@login_required
def dues():
    user = get_current_user()
    ctx = common_ctx(user)
    rows = db.get_dues(ctx["location"])
    total = db.pending_dues_total(ctx["location"])
    return render_template("dues.html", dues=rows, total_pending=total, **ctx)

@bp.route("/dues/add", methods=["POST"])
@login_required
def dues_add():
    user = get_current_user()
    loc = get_active_location(user)
    name = request.form.get("customer_name", "").strip()
    total = float(request.form.get("total_amount") or 0)
    if not name or total <= 0:
        flash("Name and amount required", "error")
        return redirect(url_for("main.dues"))
    db.add_due(loc, name, total,
               paid_amount=float(request.form.get("paid_amount") or 0),
               due_date=request.form.get("due_date") or datetime.now().strftime("%Y-%m-%d"),
               notes=request.form.get("notes", ""))
    flash("Due added", "success")
    return redirect(url_for("main.dues"))

@bp.route("/dues/<int:did>/pay", methods=["POST"])
@login_required
def dues_pay(did):
    user = get_current_user()
    amount = float(request.form.get("amount") or 0)
    if amount > 0:
        db.record_due_payment(did, get_active_location(user), amount)
        flash("Payment recorded", "success")
    return redirect(url_for("main.dues"))

@bp.route("/dues/delete/<int:did>", methods=["POST"])
@login_required
def dues_delete(did):
    user = get_current_user()
    if not can_edit(user):
        flash("Only Owner can delete", "error")
        return redirect(url_for("main.dues"))
    db.delete_due(did, get_active_location(user))
    flash("Deleted", "success")
    return redirect(url_for("main.dues"))

# ---------- EMPLOYEES ----------
@bp.route("/employees")
@login_required
def employees():
    user = get_current_user()
    ctx = common_ctx(user)
    rows = db.get_employees(ctx["location"])
    return render_template("employees.html", employees=rows, **ctx)

@bp.route("/employees/add", methods=["POST"])
@login_required
def employees_add():
    user = get_current_user()
    if not can_edit(user):
        flash("Only Owner can manage employees", "error")
        return redirect(url_for("main.employees"))
    loc = get_active_location(user)
    name = request.form.get("name", "").strip()
    if not name:
        flash("Name required", "error")
        return redirect(url_for("main.employees"))
    db.add_employee(loc, name, phone=request.form.get("phone", ""),
                    role=request.form.get("role", "Staff"),
                    monthly_salary=float(request.form.get("salary") or 0),
                    joining_date=request.form.get("joining_date", ""),
                    status=request.form.get("status", "Active"))
    flash("Employee added", "success")
    return redirect(url_for("main.employees"))

@bp.route("/employees/delete/<int:eid>", methods=["POST"])
@login_required
def employees_delete(eid):
    user = get_current_user()
    if not can_edit(user):
        flash("Only Owner can delete", "error")
        return redirect(url_for("main.employees"))
    db.delete_employee(eid, get_active_location(user))
    flash("Deleted", "success")
    return redirect(url_for("main.employees"))

# ---------- VENDORS ----------
@bp.route("/vendors")
@login_required
def vendors():
    user = get_current_user()
    ctx = common_ctx(user)
    vendors_list = db.get_vendors(ctx["location"])
    orders = db.get_vendor_orders(ctx["location"])
    stock = db.get_inventory()
    return render_template("vendors.html", vendors=vendors_list, orders=orders, stock=stock, **ctx)

@bp.route("/vendors/add", methods=["POST"])
@login_required
def vendors_add():
    user = get_current_user()
    loc = get_active_location(user)
    name = request.form.get("name", "").strip()
    if name:
        db.add_vendor(loc, name, phone=request.form.get("phone", ""),
                      address=request.form.get("address", ""), notes=request.form.get("notes", ""))
        flash("Vendor added", "success")
    return redirect(url_for("main.vendors"))

@bp.route("/vendors/order", methods=["POST"])
@login_required
def vendors_order():
    user = get_current_user()
    loc = get_active_location(user)
    db.add_vendor_order(loc, request.form.get("vendor_name", ""),
                        request.form.get("item_name", ""),
                        float(request.form.get("quantity") or 0),
                        unit=request.form.get("unit", "pcs"),
                        unit_price=float(request.form.get("unit_price") or 0),
                        notes=request.form.get("notes", ""))
    flash("Order placed & stock received automatically (shared inventory updated)", "success")
    return redirect(url_for("main.vendors"))

@bp.route("/vendors/receive/<int:oid>", methods=["POST"])
@login_required
def vendors_receive(oid):
    user = get_current_user()
    if db.receive_vendor_order(oid, get_active_location(user)):
        flash("Order received — stock updated (shared)", "success")
    return redirect(url_for("main.vendors"))

@bp.route("/vendors/delete/<int:vid>", methods=["POST"])
@login_required
def vendors_delete(vid):
    user = get_current_user()
    if not can_edit(user):
        flash("Only Owner can delete", "error")
        return redirect(url_for("main.vendors"))
    db.delete_vendor(vid, get_active_location(user))
    flash("Deleted", "success")
    return redirect(url_for("main.vendors"))

# ---------- VISITS ----------
@bp.route("/visits")
@login_required
def visits():
    user = get_current_user()
    ctx = common_ctx(user)
    rows = db.get_visits(ctx["location"])
    return render_template("visits.html", visits=rows, **ctx)

@bp.route("/visits/add", methods=["POST"])
@login_required
def visits_add():
    user = get_current_user()
    loc = get_active_location(user)
    name = request.form.get("customer_name", "").strip()
    if name:
        db.add_visit(loc, name, phone=request.form.get("phone", ""),
                     visit_date=request.form.get("visit_date") or datetime.now().strftime("%Y-%m-%d"),
                     notes=request.form.get("notes", ""))
        flash("Visit added (3-day reminder set)", "success")
    return redirect(url_for("main.visits"))

@bp.route("/visits/delete/<int:vid>", methods=["POST"])
@login_required
def visits_delete(vid):
    user = get_current_user()
    if not can_edit(user):
        flash("Only Owner can delete", "error")
        return redirect(url_for("main.visits"))
    db.delete_visit(vid, get_active_location(user))
    flash("Deleted", "success")
    return redirect(url_for("main.visits"))

# ---------- SHOPKEEPERS ----------
@bp.route("/shopkeepers")
@login_required
def shopkeepers():
    user = get_current_user()
    ctx = common_ctx(user)
    sk = db.get_shopkeepers(ctx["location"])
    ledger = db.get_shopkeeper_ledger(ctx["location"])
    return render_template("shopkeepers.html", shopkeepers=sk, ledger=ledger, **ctx)

@bp.route("/shopkeepers/add", methods=["POST"])
@login_required
def shopkeepers_add():
    user = get_current_user()
    loc = get_active_location(user)
    name = request.form.get("name", "").strip()
    if name:
        db.add_shopkeeper(loc, name, phone=request.form.get("phone", ""),
                          address=request.form.get("address", ""), notes=request.form.get("notes", ""))
        flash("Shopkeeper added", "success")
    return redirect(url_for("main.shopkeepers"))

@bp.route("/shopkeepers/ledger", methods=["POST"])
@login_required
def shopkeepers_ledger():
    user = get_current_user()
    loc = get_active_location(user)
    db.add_shop_ledger_entry(loc, request.form.get("customer_name", ""),
                             request.form.get("date") or datetime.now().strftime("%Y-%m-%d"),
                             description=request.form.get("description", ""),
                             debit=float(request.form.get("debit") or 0),
                             credit=float(request.form.get("credit") or 0),
                             notes=request.form.get("notes", ""))
    flash("Ledger entry added", "success")
    return redirect(url_for("main.shopkeepers"))

@bp.route("/shopkeepers/delete/<int:sid>", methods=["POST"])
@login_required
def shopkeepers_delete(sid):
    user = get_current_user()
    if not can_edit(user):
        flash("Only Owner can delete", "error")
        return redirect(url_for("main.shopkeepers"))
    db.delete_shopkeeper(sid, get_active_location(user))
    flash("Deleted", "success")
    return redirect(url_for("main.shopkeepers"))


# ---------- EXCEL EXPORTS ----------
@bp.route("/stock/excel")
@login_required
def stock_excel():
    user = get_current_user()
    try:
        rows = db.get_inventory() or []
        data = []
        for r in rows:
            if not isinstance(r, dict):
                try:
                    r = dict(r)
                except Exception:
                    continue
            data.append([
                r.get("item_name"), r.get("category"), r.get("quantity"), r.get("unit"),
                r.get("min_stock"), r.get("purchase_price"), r.get("sale_price"), r.get("notes"),
            ])
        return _excel_response("stock_shared.xlsx",
            ["Item Name", "Category", "Qty", "Unit", "Min Stock", "Purchase", "Sale", "Notes"], data)
    except Exception as e:
        flash(f"Excel error: {e}", "error")
        return redirect(url_for("main.stock"))

@bp.route("/customers/excel")
@login_required
def customers_excel():
    user = get_current_user()
    loc = get_active_location(user)
    try:
        rows = db.get_customers(loc) or []
        data = [[r.get("name"), r.get("phone"), r.get("email"), r.get("address"),
                 r.get("project_status"), r.get("notes")] for r in rows if isinstance(r, dict)]
        return _excel_response(f"customers_{loc}.xlsx",
            ["Name", "Phone", "Email", "Address", "Status", "Notes"], data)
    except Exception as e:
        flash(f"Excel error: {e}", "error")
        return redirect(url_for("main.customers"))

@bp.route("/expenses/excel")
@login_required
def expenses_excel():
    user = get_current_user()
    loc = get_active_location(user)
    try:
        rows = db.get_expenses(loc) or []
        data = [[r.get("date"), r.get("category"), r.get("amount"), r.get("description")]
                for r in rows if isinstance(r, dict)]
        return _excel_response(f"expenses_{loc}.xlsx",
            ["Date", "Category", "Amount", "Description"], data)
    except Exception as e:
        flash(f"Excel error: {e}", "error")
        return redirect(url_for("main.expenses"))

@bp.route("/quotations/excel")
@login_required
def quotations_excel():
    user = get_current_user()
    loc = get_active_location(user)
    try:
        rows = db.get_quotations(loc) or []
        data = [[r.get("quote_no"), r.get("customer_name"), r.get("customer_phone"),
                 r.get("date"), r.get("total"), r.get("status")]
                for r in rows if isinstance(r, dict)]
        return _excel_response(f"quotations_{loc}.xlsx",
            ["Quote No", "Customer", "Phone", "Date", "Total", "Status"], data)
    except Exception as e:
        flash(f"Excel error: {e}", "error")
        return redirect(url_for("main.quotations"))

@bp.route("/dues/excel")
@login_required
def dues_excel():
    user = get_current_user()
    loc = get_active_location(user)
    try:
        rows = db.get_dues(loc) or []
        data = [[r.get("customer_name"), r.get("invoice_no"), r.get("total_amount"),
                 r.get("paid_amount"), r.get("due_date"), r.get("status"), r.get("notes")]
                for r in rows if isinstance(r, dict)]
        return _excel_response(f"dues_{loc}.xlsx",
            ["Customer", "Invoice", "Total", "Paid", "Due Date", "Status", "Notes"], data)
    except Exception as e:
        flash(f"Excel error: {e}", "error")
        return redirect(url_for("main.dues"))

@bp.route("/employees/excel")
@login_required
def employees_excel():
    user = get_current_user()
    loc = get_active_location(user)
    try:
        rows = db.get_employees(loc) or []
        data = [[r.get("name"), r.get("phone"), r.get("role"), r.get("monthly_salary"),
                 r.get("joining_date"), r.get("status")]
                for r in rows if isinstance(r, dict)]
        return _excel_response(f"employees_{loc}.xlsx",
            ["Name", "Phone", "Role", "Salary", "Joining Date", "Status"], data)
    except Exception as e:
        flash(f"Excel error: {e}", "error")
        return redirect(url_for("main.employees"))

@bp.route("/vendors/excel")
@login_required
def vendors_excel():
    user = get_current_user()
    loc = get_active_location(user)
    try:
        rows = db.get_vendors(loc) or []
        data = [[r.get("name"), r.get("phone"), r.get("address"), r.get("notes")]
                for r in rows if isinstance(r, dict)]
        return _excel_response(f"vendors_{loc}.xlsx",
            ["Name", "Phone", "Address", "Notes"], data)
    except Exception as e:
        flash(f"Excel error: {e}", "error")
        return redirect(url_for("main.vendors"))

@bp.route("/visits/excel")
@login_required
def visits_excel():
    user = get_current_user()
    loc = get_active_location(user)
    try:
        rows = db.get_visits(loc) or []
        data = [[r.get("customer_name"), r.get("phone"), r.get("visit_date"),
                 r.get("notes"), r.get("reminder_date")]
                for r in rows if isinstance(r, dict)]
        return _excel_response(f"visits_{loc}.xlsx",
            ["Customer", "Phone", "Visit Date", "Notes", "Reminder"], data)
    except Exception as e:
        flash(f"Excel error: {e}", "error")
        return redirect(url_for("main.visits"))

@bp.route("/shopkeepers/excel")
@login_required
def shopkeepers_excel():
    user = get_current_user()
    loc = get_active_location(user)
    try:
        rows = db.get_shopkeepers(loc) or []
        data = [[r.get("name"), r.get("phone"), r.get("address"), r.get("notes")]
                for r in rows if isinstance(r, dict)]
        return _excel_response(f"shopkeepers_{loc}.xlsx",
            ["Name", "Phone", "Address", "Notes"], data)
    except Exception as e:
        flash(f"Excel error: {e}", "error")
        return redirect(url_for("main.shopkeepers"))

# ---------- PROFIT ----------
@bp.route("/profit")
@login_required
def profit():
    user = get_current_user()
    if user["role"] != "owner":
        flash("Profit section is locked for Employee accounts", "error")
        return redirect(url_for("main.dashboard"))
    ctx = common_ctx(user)
    loc = ctx["location"]
    sales = db.month_sales_total(loc)
    expenses = db.month_expenses_total(loc)
    # Simple COGS estimate from inventory purchase prices is complex; show revenue - expenses
    return render_template("profit.html", sales=sales, expenses=expenses, net=sales - expenses, **ctx)

# ---------- SETTINGS ----------
@bp.route("/settings")
@login_required
def settings():
    user = get_current_user()
    if not user or user.get("role") != "owner":
        flash("Settings are only available to the Owner account", "error")
        return redirect(url_for("main.dashboard"))
    ctx = common_ctx(user)
    return render_template("settings.html",
        alert_phone=Config.ALERT_PHONE, alert_email=Config.ALERT_EMAIL, **ctx)
