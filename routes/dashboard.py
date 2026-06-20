from datetime import date
from sqlalchemy import func
from flask import Blueprint, render_template, session
from extensions import db
from models import Voucher, Product, Party, LedgerEntry
from utils import login_required_full, current_fy, fy_range

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required_full
def index():
    fy = current_fy()
    start, end = fy_range(fy)

    sales_total = db.session.query(func.coalesce(func.sum(Voucher.grand_total), 0)).filter(
        Voucher.voucher_type == "sales",
        Voucher.voucher_date.between(start, end),
        Voucher.status == "posted",
    ).scalar() or 0

    purchase_total = db.session.query(func.coalesce(func.sum(Voucher.grand_total), 0)).filter(
        Voucher.voucher_type == "purchase",
        Voucher.voucher_date.between(start, end),
        Voucher.status == "posted",
    ).scalar() or 0

    gst_collected = db.session.query(
        func.coalesce(func.sum(Voucher.cgst_amount + Voucher.sgst_amount + Voucher.igst_amount), 0)
    ).filter(
        Voucher.voucher_type == "sales",
        Voucher.voucher_date.between(start, end),
        Voucher.status == "posted",
    ).scalar() or 0

    product_count = Product.query.filter_by(is_active=True).count()
    party_count = Party.query.count()

    low_stock = Product.query.filter(
        Product.is_active.is_(True),
        Product.stock_qty <= Product.reorder_level,
    ).limit(10).all()

    recent = Voucher.query.filter(
        Voucher.voucher_date.between(start, end),
    ).order_by(Voucher.id.desc()).limit(10).all()

    return render_template(
        "dashboard.html",
        fy=fy, sales_total=sales_total, purchase_total=purchase_total,
        gst_collected=gst_collected, product_count=product_count,
        party_count=party_count, low_stock=low_stock, recent=recent,
    )
