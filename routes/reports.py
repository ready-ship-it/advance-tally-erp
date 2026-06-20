from datetime import date
from io import BytesIO
from sqlalchemy import func, extract
from flask import Blueprint, render_template, request, send_file
from extensions import db
from models import Voucher, Ledger, LedgerEntry
from services.export_service import gst_summary_to_xlsx, gst_summary_to_pdf
from utils import login_required_full, current_fy, fy_range

bp = Blueprint("reports", __name__)


def _gst_monthly_rows(fy: int):
    start, end = fy_range(fy)
    rows = db.session.query(
        extract("year", Voucher.voucher_date).label("y"),
        extract("month", Voucher.voucher_date).label("m"),
        func.coalesce(func.sum(Voucher.taxable_value), 0).label("taxable"),
        func.coalesce(func.sum(Voucher.cgst_amount), 0).label("cgst"),
        func.coalesce(func.sum(Voucher.sgst_amount), 0).label("sgst"),
        func.coalesce(func.sum(Voucher.igst_amount), 0).label("igst"),
        func.coalesce(func.sum(Voucher.grand_total), 0).label("total"),
    ).filter(
        Voucher.voucher_type == "sales",
        Voucher.voucher_date.between(start, end),
        Voucher.status == "posted",
    ).group_by("y", "m").order_by("y", "m").all()

    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    return [{
        "period": f"{months[int(r.m)-1]}-{int(r.y)}",
        "taxable": float(r.taxable or 0),
        "cgst": float(r.cgst or 0),
        "sgst": float(r.sgst or 0),
        "igst": float(r.igst or 0),
        "total_gst": float((r.cgst or 0) + (r.sgst or 0) + (r.igst or 0)),
        "total": float(r.total or 0),
    } for r in rows]


@bp.route("/gst-monthly")
@login_required_full
def gst_monthly():
    fy = current_fy()
    rows = _gst_monthly_rows(fy)
    totals = {
        k: sum(r[k] for r in rows)
        for k in ("taxable", "cgst", "sgst", "igst", "total_gst", "total")
    } if rows else {k: 0 for k in ("taxable","cgst","sgst","igst","total_gst","total")}
    return render_template("report_gst.html", rows=rows, totals=totals, fy=fy)


@bp.route("/gst-monthly/export.<fmt>")
@login_required_full
def gst_export(fmt):
    fy = current_fy()
    rows = _gst_monthly_rows(fy)
    if fmt == "xlsx":
        buf = gst_summary_to_xlsx(rows, fy)
        return send_file(buf, as_attachment=True,
                         download_name=f"GST_Monthly_FY{fy}-{str(fy+1)[2:]}.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if fmt == "pdf":
        buf = gst_summary_to_pdf(rows, fy)
        return send_file(buf, as_attachment=True,
                         download_name=f"GST_Monthly_FY{fy}-{str(fy+1)[2:]}.pdf",
                         mimetype="application/pdf")
    return ("Unsupported format", 400)


@bp.route("/day-book")
@login_required_full
def day_book():
    fy = current_fy()
    start, end = fy_range(fy)
    d_from = request.args.get("from") or start.isoformat()
    d_to = request.args.get("to") or end.isoformat()
    vouchers = Voucher.query.filter(
        Voucher.voucher_date.between(d_from, d_to)
    ).order_by(Voucher.voucher_date, Voucher.id).all()
    return render_template("report_daybook.html", vouchers=vouchers, d_from=d_from, d_to=d_to)


@bp.route("/ledger/<int:lid>")
@login_required_full
def ledger_statement(lid):
    fy = current_fy()
    start, end = fy_range(fy)
    l = Ledger.query.get_or_404(lid)
    entries = LedgerEntry.query.filter(
        LedgerEntry.ledger_id == lid,
        LedgerEntry.entry_date.between(start, end),
    ).order_by(LedgerEntry.entry_date, LedgerEntry.id).all()
    running = l.opening_balance or 0
    out = []
    for e in entries:
        running += (e.debit or 0) - (e.credit or 0)
        out.append((e, running))
    return render_template("report_ledger.html", ledger=l, entries=out, opening=l.opening_balance or 0)


@bp.route("/ledgers")
@login_required_full
def ledger_list():
    ls = Ledger.query.order_by(Ledger.group_name, Ledger.name).all()
    return render_template("ledger_list.html", ledgers=ls)


@bp.route("/profit-loss")
@login_required_full
def pnl():
    fy = current_fy()
    start, end = fy_range(fy)

    def _sum(group_prefix):
        return db.session.query(func.coalesce(func.sum(LedgerEntry.credit - LedgerEntry.debit), 0)
        ).join(Ledger).filter(
            Ledger.group_name.like(f"{group_prefix}%"),
            LedgerEntry.entry_date.between(start, end),
        ).scalar() or 0

    sales = _sum("Sales")
    purchase = -_sum("Purchase")  # Dr nature flipped
    direct_exp = -_sum("Direct Expenses")
    indirect_exp = -_sum("Indirect Expenses")
    indirect_inc = _sum("Indirect Incomes")
    gross = sales - purchase - direct_exp
    net = gross + indirect_inc - indirect_exp
    return render_template("report_pnl.html",
                           sales=sales, purchase=purchase, direct_exp=direct_exp,
                           indirect_exp=indirect_exp, indirect_inc=indirect_inc,
                           gross=gross, net=net, fy=fy)
