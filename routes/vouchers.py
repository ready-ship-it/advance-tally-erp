from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import current_user
from extensions import db
from models import Voucher, VoucherItem, Product, Party, Ledger, LedgerEntry
from utils import login_required_full, current_fy, fy_range

bp = Blueprint("vouchers", __name__)


# ---------- Helpers ----------
def _next_voucher_no(vtype: str, fy: int) -> str:
    prefix = {
        "sales": "INV", "purchase": "PUR", "receipt": "RCT",
        "payment": "PAY", "journal": "JV",
    }.get(vtype, "VCH")
    last = Voucher.query.filter_by(voucher_type=vtype, fy_year=fy).order_by(Voucher.id.desc()).first()
    seq = 1
    if last:
        try:
            seq = int(last.voucher_no.split("-")[-1]) + 1
        except Exception:
            seq = (last.id or 0) + 1
    return f"{prefix}-{fy}-{seq:05d}"


def _ledger_get_or_create(name: str, group: str) -> Ledger:
    l = Ledger.query.filter_by(name=name).first()
    if not l:
        l = Ledger(name=name, group_name=group)
        db.session.add(l)
        db.session.flush()
    return l


def _post_double_entry(v: Voucher):
    """Create LedgerEntry rows for a posted voucher (Indian-style)."""
    if v.voucher_type == "sales":
        party_l = _ledger_get_or_create(v.party.name if v.party else "Cash Sales",
                                        "Sundry Debtors" if v.party else "Cash-in-hand")
        sales_l = _ledger_get_or_create("Sales Account", "Sales Accounts")
        cgst_l = _ledger_get_or_create("Output CGST", "Duties & Taxes")
        sgst_l = _ledger_get_or_create("Output SGST", "Duties & Taxes")
        igst_l = _ledger_get_or_create("Output IGST", "Duties & Taxes")
        # Dr Party, Cr Sales + Cr GST
        db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=party_l.id, entry_date=v.voucher_date,
                                   fy_year=v.fy_year, debit=v.grand_total, narration=v.voucher_no))
        db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=sales_l.id, entry_date=v.voucher_date,
                                   fy_year=v.fy_year, credit=v.taxable_value, narration=v.voucher_no))
        if v.cgst_amount:
            db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=cgst_l.id, entry_date=v.voucher_date,
                                       fy_year=v.fy_year, credit=v.cgst_amount, narration=v.voucher_no))
        if v.sgst_amount:
            db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=sgst_l.id, entry_date=v.voucher_date,
                                       fy_year=v.fy_year, credit=v.sgst_amount, narration=v.voucher_no))
        if v.igst_amount:
            db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=igst_l.id, entry_date=v.voucher_date,
                                       fy_year=v.fy_year, credit=v.igst_amount, narration=v.voucher_no))
    elif v.voucher_type == "purchase":
        party_l = _ledger_get_or_create(v.party.name if v.party else "Cash Purchase",
                                        "Sundry Creditors" if v.party else "Cash-in-hand")
        purchase_l = _ledger_get_or_create("Purchase Account", "Purchase Accounts")
        cgst_l = _ledger_get_or_create("Input CGST", "Duties & Taxes")
        sgst_l = _ledger_get_or_create("Input SGST", "Duties & Taxes")
        igst_l = _ledger_get_or_create("Input IGST", "Duties & Taxes")
        db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=purchase_l.id, entry_date=v.voucher_date,
                                   fy_year=v.fy_year, debit=v.taxable_value, narration=v.voucher_no))
        if v.cgst_amount:
            db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=cgst_l.id, entry_date=v.voucher_date,
                                       fy_year=v.fy_year, debit=v.cgst_amount, narration=v.voucher_no))
        if v.sgst_amount:
            db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=sgst_l.id, entry_date=v.voucher_date,
                                       fy_year=v.fy_year, debit=v.sgst_amount, narration=v.voucher_no))
        if v.igst_amount:
            db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=igst_l.id, entry_date=v.voucher_date,
                                       fy_year=v.fy_year, debit=v.igst_amount, narration=v.voucher_no))
        db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=party_l.id, entry_date=v.voucher_date,
                                   fy_year=v.fy_year, credit=v.grand_total, narration=v.voucher_no))
    elif v.voucher_type == "receipt":
        cash_l = _ledger_get_or_create("Cash" if v.payment_mode == "cash" else "Bank",
                                       "Cash-in-hand" if v.payment_mode == "cash" else "Bank Accounts")
        party_l = _ledger_get_or_create(v.party.name if v.party else "Other Receipts",
                                        "Sundry Debtors" if v.party else "Indirect Incomes")
        db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=cash_l.id, entry_date=v.voucher_date,
                                   fy_year=v.fy_year, debit=v.grand_total, narration=v.voucher_no))
        db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=party_l.id, entry_date=v.voucher_date,
                                   fy_year=v.fy_year, credit=v.grand_total, narration=v.voucher_no))
    elif v.voucher_type == "payment":
        cash_l = _ledger_get_or_create("Cash" if v.payment_mode == "cash" else "Bank",
                                       "Cash-in-hand" if v.payment_mode == "cash" else "Bank Accounts")
        party_l = _ledger_get_or_create(v.party.name if v.party else "Other Expenses",
                                        "Sundry Creditors" if v.party else "Indirect Expenses")
        db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=party_l.id, entry_date=v.voucher_date,
                                   fy_year=v.fy_year, debit=v.grand_total, narration=v.voucher_no))
        db.session.add(LedgerEntry(voucher_id=v.id, ledger_id=cash_l.id, entry_date=v.voucher_date,
                                   fy_year=v.fy_year, credit=v.grand_total, narration=v.voucher_no))


def _adjust_stock(v: Voucher, sign: int):
    """sign=+1 for purchase (add), -1 for sales (deduct)."""
    for item in v.items:
        if item.product_id:
            p = Product.query.get(item.product_id)
            if p:
                p.stock_qty = (p.stock_qty or 0) + sign * (item.qty or 0)


# ---------- List ----------
@bp.route("/<vtype>")
@login_required_full
def list_vouchers(vtype):
    if vtype not in ("sales", "purchase", "receipt", "payment", "journal"):
        abort(404)
    fy = current_fy()
    start, end = fy_range(fy)
    items = Voucher.query.filter(
        Voucher.voucher_type == vtype,
        Voucher.voucher_date.between(start, end),
    ).order_by(Voucher.voucher_date.desc(), Voucher.id.desc()).all()
    return render_template("voucher_list.html", vouchers=items, vtype=vtype)


# ---------- Create Sales / Purchase ----------
@bp.route("/<vtype>/new", methods=["GET", "POST"])
@login_required_full
def new_invoice(vtype):
    if vtype not in ("sales", "purchase"):
        abort(404)
    fy = current_fy()
    if request.method == "POST":
        data = request.get_json(force=True)
        party_id = data.get("party_id") or None
        party = Party.query.get(int(party_id)) if party_id else None
        is_interstate = bool(data.get("is_interstate"))

        v = Voucher(
            voucher_type=vtype,
            voucher_no=_next_voucher_no(vtype, fy),
            voucher_date=datetime.strptime(data["voucher_date"], "%Y-%m-%d").date(),
            fy_year=fy,
            party_id=party.id if party else None,
            reference=data.get("reference", ""),
            narration=data.get("narration", ""),
            is_interstate=is_interstate,
            payment_mode=data.get("payment_mode", "credit"),
            created_by=current_user.id,
        )
        sub = tax = cgst = sgst = igst = 0.0
        for row in data.get("items", []):
            qty = float(row.get("qty", 0))
            rate = float(row.get("rate", 0))
            disc = float(row.get("discount_pct", 0))
            gst_rate = float(row.get("gst_rate", 18))
            taxable = round(qty * rate * (1 - disc / 100.0), 2)
            if is_interstate:
                ig = round(taxable * gst_rate / 100.0, 2); cg = sg = 0.0
            else:
                cg = sg = round(taxable * (gst_rate / 2) / 100.0, 2); ig = 0.0
            line_total = round(taxable + cg + sg + ig, 2)
            sub += round(qty * rate, 2); tax += taxable
            cgst += cg; sgst += sg; igst += ig
            v.items.append(VoucherItem(
                product_id=int(row["product_id"]) if row.get("product_id") else None,
                description=row.get("description", ""),
                hsn_code=row.get("hsn_code", ""),
                qty=qty, unit=row.get("unit", "PCS"), rate=rate,
                discount_pct=disc, taxable_value=taxable, gst_rate=gst_rate,
                cgst_amount=cg, sgst_amount=sg, igst_amount=ig, line_total=line_total,
            ))
        v.sub_total = round(sub, 2)
        v.discount = round(sub - tax, 2)
        v.taxable_value = round(tax, 2)
        v.cgst_amount = round(cgst, 2)
        v.sgst_amount = round(sgst, 2)
        v.igst_amount = round(igst, 2)
        raw_total = tax + cgst + sgst + igst
        rounded = round(raw_total)
        v.round_off = round(rounded - raw_total, 2)
        v.grand_total = rounded
        db.session.add(v); db.session.flush()
        _post_double_entry(v)
        _adjust_stock(v, sign=+1 if vtype == "purchase" else -1)
        db.session.commit()
        return jsonify({"ok": True, "id": v.id, "voucher_no": v.voucher_no})

    parties = Party.query.order_by(Party.name).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    return render_template("voucher_invoice.html", vtype=vtype, parties=parties,
                           products=products, today=date.today().isoformat())


# ---------- Receipt / Payment ----------
@bp.route("/<vtype>/cash/new", methods=["GET", "POST"])
@login_required_full
def new_cash_voucher(vtype):
    if vtype not in ("receipt", "payment"):
        abort(404)
    fy = current_fy()
    if request.method == "POST":
        party_id = request.form.get("party_id") or None
        amt = float(request.form.get("amount", 0) or 0)
        v = Voucher(
            voucher_type=vtype,
            voucher_no=_next_voucher_no(vtype, fy),
            voucher_date=datetime.strptime(request.form["voucher_date"], "%Y-%m-%d").date(),
            fy_year=fy,
            party_id=int(party_id) if party_id else None,
            narration=request.form.get("narration", ""),
            payment_mode=request.form.get("payment_mode", "cash"),
            grand_total=amt,
            taxable_value=amt,
            created_by=current_user.id,
        )
        db.session.add(v); db.session.flush()
        _post_double_entry(v)
        db.session.commit()
        flash(f"{vtype.title()} {v.voucher_no} created", "success")
        return redirect(url_for("vouchers.list_vouchers", vtype=vtype))
    parties = Party.query.order_by(Party.name).all()
    return render_template("voucher_cash.html", vtype=vtype, parties=parties,
                           today=date.today().isoformat())


# ---------- View ----------
@bp.route("/view/<int:vid>")
@login_required_full
def view(vid):
    v = Voucher.query.get_or_404(vid)
    return render_template("voucher_view.html", v=v)
