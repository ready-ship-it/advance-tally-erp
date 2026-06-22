"""Bank reconciliation routes."""
from datetime import datetime, date
from io import BytesIO
import json
import csv
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from extensions import db
from models.bank import BankAccount, BankStatement, BankReconciliation, OutstandingCheck, DepositInTransit, BankCharge
from models import Ledger, LedgerEntry
from services.bank_service import (
    create_bank_account, import_bank_statement, get_unreconciled_statements,
    get_unmatched_ledger_entries, reconcile_statement, create_reconciliation_session,
    get_reconciliation_report, record_outstanding_check, record_deposit_in_transit,
    record_bank_charge, clear_outstanding_check, clear_deposit_in_transit
)
from utils import login_required_full, admin_required
from flask_login import current_user

bp = Blueprint("bank", __name__, url_prefix="/bank")


# ---------- Bank Account Management ----------
@bp.route("/accounts")
@login_required_full
def list_accounts():
    """List all bank accounts."""
    accounts = BankAccount.query.filter_by(is_active=True).all()
    return render_template("bank_accounts.html", accounts=accounts)


@bp.route("/accounts/new", methods=["GET", "POST"])
@admin_required
def new_account():
    """Create a new bank account."""
    if request.method == "POST":
        account_name = request.form.get("account_name", "").strip()
        account_number = request.form.get("account_number", "").strip()
        ifsc_code = request.form.get("ifsc_code", "").strip()
        bank_name = request.form.get("bank_name", "").strip()
        branch_name = request.form.get("branch_name", "").strip()
        opening_balance = request.form.get("opening_balance", type=float, default=0.0)
        
        if not account_name or not account_number:
            flash("Account name and number are required", "error")
            return redirect(url_for("bank.new_account"))
        
        existing = BankAccount.query.filter_by(account_number=account_number).first()
        if existing:
            flash("Account number already exists", "error")
            return redirect(url_for("bank.new_account"))
        
        account = create_bank_account(
            account_name, account_number, ifsc_code, bank_name, branch_name, opening_balance
        )
        flash(f"Bank account '{account_name}' created", "success")
        return redirect(url_for("bank.view_account", aid=account.id))
    
    return render_template("bank_account_form.html")


@bp.route("/accounts/<int:aid>")
@login_required_full
def view_account(aid):
    """View bank account details."""
    account = BankAccount.query.get_or_404(aid)
    statements = BankStatement.query.filter_by(account_id=aid).order_by(BankStatement.transaction_date.desc()).limit(50).all()
    unreconciled = get_unreconciled_statements(aid)
    
    return render_template("bank_account_view.html", account=account, statements=statements, unreconciled_count=len(unreconciled))


@bp.route("/accounts/<int:aid>/edit", methods=["GET", "POST"])
@admin_required
def edit_account(aid):
    """Edit bank account."""
    account = BankAccount.query.get_or_404(aid)
    
    if request.method == "POST":
        account.account_name = request.form.get("account_name", account.account_name).strip()
        account.bank_name = request.form.get("bank_name", account.bank_name).strip()
        account.branch_name = request.form.get("branch_name", account.branch_name).strip()
        account.ifsc_code = request.form.get("ifsc_code", account.ifsc_code).strip()
        account.is_active = bool(request.form.get("is_active"))
        db.session.commit()
        flash("Account updated", "success")
        return redirect(url_for("bank.view_account", aid=aid))
    
    return render_template("bank_account_form.html", account=account)


# ---------- Statement Import ----------
@bp.route("/accounts/<int:aid>/import", methods=["GET", "POST"])
@login_required_full
def import_statement(aid):
    """Import bank statement from CSV."""
    account = BankAccount.query.get_or_404(aid)
    
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file provided", "error")
            return redirect(url_for("bank.import_statement", aid=aid))
        
        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "error")
            return redirect(url_for("bank.import_statement", aid=aid))
        
        try:
            # Parse CSV
            stream = file.stream.read().decode("UTF8").splitlines()
            reader = csv.DictReader(stream)
            
            statement_data = []
            for row in reader:
                statement_data.append({
                    "transaction_date": datetime.strptime(row.get("date"), "%d-%m-%Y").date(),
                    "description": row.get("description", ""),
                    "reference": row.get("reference", ""),
                    "debit": float(row.get("debit", 0) or 0),
                    "credit": float(row.get("credit", 0) or 0),
                    "balance": float(row.get("balance", 0) or 0)
                })
            
            success, message = import_bank_statement(aid, statement_data)
            if success:
                flash(message, "success")
            else:
                flash(message, "error")
        except Exception as e:
            flash(f"Error importing file: {str(e)}", "error")
        
        return redirect(url_for("bank.view_account", aid=aid))
    
    return render_template("bank_import_statement.html", account=account)


# ---------- Reconciliation ----------
@bp.route("/reconcile/<int:aid>", methods=["GET", "POST"])
@login_required_full
def reconcile(aid):
    """Start bank reconciliation."""
    account = BankAccount.query.get_or_404(aid)
    
    if request.method == "POST":
        bank_statement_date = datetime.strptime(request.form.get("statement_date"), "%Y-%m-%d").date()
        bank_closing_balance = request.form.get("closing_balance", type=float)
        
        reconciliation = create_reconciliation_session(aid, bank_statement_date, bank_closing_balance, current_user.id)
        flash("Reconciliation session started", "success")
        return redirect(url_for("bank.reconciliation_detail", rid=reconciliation.id))
    
    return render_template("bank_reconcile.html", account=account)


@bp.route("/reconciliation/<int:rid>")
@login_required_full
def reconciliation_detail(rid):
    """View reconciliation details."""
    reconciliation = BankReconciliation.query.get_or_404(rid)
    
    unreconciled = get_unreconciled_statements(reconciliation.account_id)
    unmatched_entries = get_unmatched_ledger_entries(
        reconciliation.account_id,
        reconciliation.bank_statement_date - __import__('datetime').timedelta(days=30),
        reconciliation.bank_statement_date
    )
    
    report = get_reconciliation_report(reconciliation.account_id, reconciliation.bank_statement_date)
    
    return render_template("bank_reconciliation_detail.html", 
                          reconciliation=reconciliation,
                          unreconciled=unreconciled,
                          unmatched_entries=unmatched_entries,
                          report=report)


@bp.route("/reconciliation/<int:rid>/match", methods=["POST"])
@login_required_full
def match_statement(rid):
    """Match a bank statement with a ledger entry."""
    reconciliation = BankReconciliation.query.get_or_404(rid)
    statement_id = request.form.get("statement_id", type=int)
    entry_id = request.form.get("entry_id", type=int)
    
    success, message = reconcile_statement(reconciliation.account_id, statement_id, entry_id)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
    
    return redirect(url_for("bank.reconciliation_detail", rid=rid))


@bp.route("/reconciliation/<int:rid>/finalize", methods=["POST"])
@login_required_full
def finalize_reconciliation(rid):
    """Finalize reconciliation."""
    reconciliation = BankReconciliation.query.get_or_404(rid)
    
    # Check if all unreconciled statements have been handled
    unreconciled = get_unreconciled_statements(reconciliation.account_id)
    
    if unreconciled:
        flash(f"There are still {len(unreconciled)} unreconciled statements", "error")
        return redirect(url_for("bank.reconciliation_detail", rid=rid))
    
    reconciliation.status = "reconciled"
    db.session.commit()
    
    flash("Reconciliation completed", "success")
    return redirect(url_for("bank.reconciliation_report", rid=rid))


@bp.route("/reconciliation/<int:rid>/report")
@login_required_full
def reconciliation_report(rid):
    """View reconciliation report."""
    reconciliation = BankReconciliation.query.get_or_404(rid)
    report = get_reconciliation_report(reconciliation.account_id, reconciliation.bank_statement_date)
    
    return render_template("bank_reconciliation_report.html", reconciliation=reconciliation, report=report)


# ---------- Outstanding Cheques ----------
@bp.route("/accounts/<int:aid>/cheques")
@login_required_full
def list_cheques(aid):
    """List outstanding cheques."""
    account = BankAccount.query.get_or_404(aid)
    cheques = OutstandingCheck.query.filter_by(account_id=aid, status="outstanding").all()
    
    return render_template("bank_cheques.html", account=account, cheques=cheques)


@bp.route("/accounts/<int:aid>/cheques/new", methods=["GET", "POST"])
@login_required_full
def new_cheque(aid):
    """Record a new cheque."""
    account = BankAccount.query.get_or_404(aid)
    
    if request.method == "POST":
        cheque_number = request.form.get("cheque_number", "").strip()
        cheque_date = datetime.strptime(request.form.get("cheque_date"), "%Y-%m-%d").date()
        amount = request.form.get("amount", type=float)
        payee = request.form.get("payee", "").strip()
        
        if not cheque_number or not amount:
            flash("Cheque number and amount are required", "error")
            return redirect(url_for("bank.new_cheque", aid=aid))
        
        check = record_outstanding_check(aid, cheque_number, cheque_date, amount, payee)
        flash(f"Cheque {cheque_number} recorded", "success")
        return redirect(url_for("bank.list_cheques", aid=aid))
    
    return render_template("bank_cheque_form.html", account=account)


@bp.route("/cheques/<int:cid>/clear", methods=["POST"])
@login_required_full
def clear_cheque(cid):
    """Mark cheque as cleared."""
    check = OutstandingCheck.query.get_or_404(cid)
    clear_outstanding_check(cid)
    flash(f"Cheque {check.cheque_number} marked as cleared", "success")
    return redirect(url_for("bank.list_cheques", aid=check.account_id))


# ---------- Deposits in Transit ----------
@bp.route("/accounts/<int:aid>/deposits")
@login_required_full
def list_deposits(aid):
    """List deposits in transit."""
    account = BankAccount.query.get_or_404(aid)
    deposits = DepositInTransit.query.filter_by(account_id=aid, status="pending").all()
    
    return render_template("bank_deposits.html", account=account, deposits=deposits)


@bp.route("/accounts/<int:aid>/deposits/new", methods=["GET", "POST"])
@login_required_full
def new_deposit(aid):
    """Record a new deposit."""
    account = BankAccount.query.get_or_404(aid)
    
    if request.method == "POST":
        deposit_date = datetime.strptime(request.form.get("deposit_date"), "%Y-%m-%d").date()
        amount = request.form.get("amount", type=float)
        description = request.form.get("description", "").strip()
        
        if not amount:
            flash("Amount is required", "error")
            return redirect(url_for("bank.new_deposit", aid=aid))
        
        deposit = record_deposit_in_transit(aid, deposit_date, amount, description)
        flash(f"Deposit of ₹{amount} recorded", "success")
        return redirect(url_for("bank.list_deposits", aid=aid))
    
    return render_template("bank_deposit_form.html", account=account)


@bp.route("/deposits/<int:did>/credit", methods=["POST"])
@login_required_full
def credit_deposit(did):
    """Mark deposit as credited."""
    deposit = DepositInTransit.query.get_or_404(did)
    clear_deposit_in_transit(did)
    flash(f"Deposit of ₹{deposit.amount} marked as credited", "success")
    return redirect(url_for("bank.list_deposits", aid=deposit.account_id))


# ---------- Bank Charges ----------
@bp.route("/accounts/<int:aid>/charges")
@login_required_full
def list_charges(aid):
    """List bank charges."""
    account = BankAccount.query.get_or_404(aid)
    charges = BankCharge.query.filter_by(account_id=aid, is_posted=False).all()
    
    return render_template("bank_charges.html", account=account, charges=charges)


@bp.route("/accounts/<int:aid>/charges/new", methods=["GET", "POST"])
@login_required_full
def new_charge(aid):
    """Record a new bank charge."""
    account = BankAccount.query.get_or_404(aid)
    
    if request.method == "POST":
        charge_date = datetime.strptime(request.form.get("charge_date"), "%Y-%m-%d").date()
        description = request.form.get("description", "").strip()
        amount = request.form.get("amount", type=float)
        
        if not amount:
            flash("Amount is required", "error")
            return redirect(url_for("bank.new_charge", aid=aid))
        
        charge = record_bank_charge(aid, charge_date, description, amount)
        flash(f"Charge of ₹{amount} recorded", "success")
        return redirect(url_for("bank.list_charges", aid=aid))
    
    return render_template("bank_charge_form.html", account=account)


# ---------- API Endpoints ----------
@bp.route("/api/accounts/<int:aid>/summary")
@login_required_full
def api_account_summary(aid):
    """Get account summary (API)."""
    account = BankAccount.query.get_or_404(aid)
    
    # Calculate current balance
    statements = BankStatement.query.filter_by(account_id=aid).order_by(BankStatement.transaction_date.desc()).first()
    current_balance = statements.balance if statements else account.opening_balance
    
    return jsonify({
        "account_id": aid,
        "account_name": account.account_name,
        "account_number": account.account_number,
        "opening_balance": account.opening_balance,
        "current_balance": current_balance,
        "outstanding_cheques": sum(c.amount for c in OutstandingCheck.query.filter_by(account_id=aid, status="outstanding").all()),
        "deposits_in_transit": sum(d.amount for d in DepositInTransit.query.filter_by(account_id=aid, status="pending").all()),
        "unreconciled_statements": len(get_unreconciled_statements(aid))
    })
