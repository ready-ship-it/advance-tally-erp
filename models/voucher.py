from datetime import datetime, date
from extensions import db


class Voucher(db.Model):
    __tablename__ = "vouchers"
    id = db.Column(db.Integer, primary_key=True)
    voucher_type = db.Column(db.String(20), nullable=False, index=True)  # sales, purchase, receipt, payment, journal
    voucher_no = db.Column(db.String(40), nullable=False, index=True)
    voucher_date = db.Column(db.Date, default=date.today, index=True)
    fy_year = db.Column(db.Integer, index=True)  # 2025 means FY 2025-26
    party_id = db.Column(db.Integer, db.ForeignKey("parties.id"))
    reference = db.Column(db.String(120))
    narration = db.Column(db.Text)

    # GST split
    sub_total = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    taxable_value = db.Column(db.Float, default=0.0)
    cgst_amount = db.Column(db.Float, default=0.0)
    sgst_amount = db.Column(db.Float, default=0.0)
    igst_amount = db.Column(db.Float, default=0.0)
    round_off = db.Column(db.Float, default=0.0)
    grand_total = db.Column(db.Float, default=0.0)

    is_interstate = db.Column(db.Boolean, default=False)
    payment_mode = db.Column(db.String(30))  # cash, bank, credit
    status = db.Column(db.String(20), default="posted")  # posted, draft, cancelled

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    party = db.relationship("Party")
    items = db.relationship("VoucherItem", backref="voucher", cascade="all, delete-orphan")


class VoucherItem(db.Model):
    __tablename__ = "voucher_items"
    id = db.Column(db.Integer, primary_key=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey("vouchers.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    description = db.Column(db.String(255))
    hsn_code = db.Column(db.String(20))
    qty = db.Column(db.Float, default=1.0)
    unit = db.Column(db.String(20), default="PCS")
    rate = db.Column(db.Float, default=0.0)
    discount_pct = db.Column(db.Float, default=0.0)
    taxable_value = db.Column(db.Float, default=0.0)
    gst_rate = db.Column(db.Float, default=18.0)
    cgst_amount = db.Column(db.Float, default=0.0)
    sgst_amount = db.Column(db.Float, default=0.0)
    igst_amount = db.Column(db.Float, default=0.0)
    line_total = db.Column(db.Float, default=0.0)

    product = db.relationship("Product")


class Ledger(db.Model):
    """Chart of Accounts. Each Party also gets one; manual ledgers allowed."""
    __tablename__ = "ledgers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    group_name = db.Column(db.String(60), default="Sundry Debtors")  # Indirect Income, Bank, Cash, Sales, etc.
    opening_balance = db.Column(db.Float, default=0.0)
    party_id = db.Column(db.Integer, db.ForeignKey("parties.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LedgerEntry(db.Model):
    """Double-entry posting line."""
    __tablename__ = "ledger_entries"
    id = db.Column(db.Integer, primary_key=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey("vouchers.id"))
    ledger_id = db.Column(db.Integer, db.ForeignKey("ledgers.id"), nullable=False, index=True)
    entry_date = db.Column(db.Date, default=date.today, index=True)
    fy_year = db.Column(db.Integer, index=True)
    debit = db.Column(db.Float, default=0.0)
    credit = db.Column(db.Float, default=0.0)
    narration = db.Column(db.String(255))

    ledger = db.relationship("Ledger")
    voucher = db.relationship("Voucher")


class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.Text)


class BackupLog(db.Model):
    __tablename__ = "backup_logs"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    size_bytes = db.Column(db.BigInteger, default=0)
    mode = db.Column(db.String(20), default="auto")  # auto / manual
    ftp_uploaded = db.Column(db.Boolean, default=False)
    ftp_message = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
