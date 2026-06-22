from datetime import datetime, date
from extensions import db


class BankAccount(db.Model):
    """Bank account master."""
    __tablename__ = "bank_accounts"
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(120), nullable=False)
    account_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    ifsc_code = db.Column(db.String(20))
    bank_name = db.Column(db.String(120))
    branch_name = db.Column(db.String(120))
    opening_balance = db.Column(db.Float, default=0.0)
    opening_date = db.Column(db.Date, default=date.today)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    statements = db.relationship("BankStatement", backref="account", cascade="all, delete-orphan")
    reconciliations = db.relationship("BankReconciliation", backref="account", cascade="all, delete-orphan")


class BankStatement(db.Model):
    """Bank statement line items (imported from bank)."""
    __tablename__ = "bank_statements"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("bank_accounts.id"), nullable=False, index=True)
    statement_date = db.Column(db.Date, nullable=False, index=True)
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.String(255))
    reference = db.Column(db.String(120))  # Cheque number, transaction ID, etc.
    debit = db.Column(db.Float, default=0.0)
    credit = db.Column(db.Float, default=0.0)
    balance = db.Column(db.Float, default=0.0)
    is_reconciled = db.Column(db.Boolean, default=False, index=True)
    reconciled_with_id = db.Column(db.Integer, db.ForeignKey("ledger_entries.id"), nullable=True)
    reconciliation_id = db.Column(db.Integer, db.ForeignKey("bank_reconciliations.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class BankReconciliation(db.Model):
    """Bank reconciliation session."""
    __tablename__ = "bank_reconciliations"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("bank_accounts.id"), nullable=False, index=True)
    reconciliation_date = db.Column(db.Date, default=date.today, nullable=False)
    bank_statement_date = db.Column(db.Date, nullable=False)
    bank_closing_balance = db.Column(db.Float, nullable=False)
    book_closing_balance = db.Column(db.Float, nullable=False)
    difference = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="pending")  # pending, reconciled, variance
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User")
    statement_items = db.relationship("BankStatement", backref="reconciliation_session")


class OutstandingCheck(db.Model):
    """Outstanding cheques not yet cleared."""
    __tablename__ = "outstanding_checks"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("bank_accounts.id"), nullable=False, index=True)
    cheque_number = db.Column(db.String(20), nullable=False)
    cheque_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payee = db.Column(db.String(120))
    issued_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default="outstanding")  # outstanding, cleared, cancelled
    cleared_date = db.Column(db.Date, nullable=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey("vouchers.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    account = db.relationship("BankAccount")
    voucher = db.relationship("Voucher")


class DepositInTransit(db.Model):
    """Deposits not yet credited by bank."""
    __tablename__ = "deposits_in_transit"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("bank_accounts.id"), nullable=False, index=True)
    deposit_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    status = db.Column(db.String(20), default="pending")  # pending, credited, cancelled
    credited_date = db.Column(db.Date, nullable=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey("vouchers.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    account = db.relationship("BankAccount")
    voucher = db.relationship("Voucher")


class BankCharge(db.Model):
    """Bank charges and fees."""
    __tablename__ = "bank_charges"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("bank_accounts.id"), nullable=False, index=True)
    charge_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255))
    amount = db.Column(db.Float, nullable=False)
    is_posted = db.Column(db.Boolean, default=False)
    ledger_entry_id = db.Column(db.Integer, db.ForeignKey("ledger_entries.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    account = db.relationship("BankAccount")
