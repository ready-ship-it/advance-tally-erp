"""Bank reconciliation service."""
from datetime import datetime, date
from extensions import db
from models.bank import (
    BankAccount, BankStatement, BankReconciliation,
    OutstandingCheck, DepositInTransit, BankCharge
)
from models import LedgerEntry, Ledger


def create_bank_account(account_name, account_number, ifsc_code, bank_name, branch_name, opening_balance=0.0):
    """Create a new bank account."""
    account = BankAccount(
        account_name=account_name,
        account_number=account_number,
        ifsc_code=ifsc_code,
        bank_name=bank_name,
        branch_name=branch_name,
        opening_balance=opening_balance
    )
    db.session.add(account)
    db.session.commit()
    return account


def import_bank_statement(account_id, statement_data):
    """
    Import bank statement from CSV/Excel.
    
    statement_data: List of dicts with keys:
    - transaction_date
    - description
    - reference (optional)
    - debit (optional)
    - credit (optional)
    - balance
    """
    account = BankAccount.query.get(account_id)
    if not account:
        return False, "Account not found"
    
    imported_count = 0
    for row in statement_data:
        # Check if statement already exists
        existing = BankStatement.query.filter_by(
            account_id=account_id,
            transaction_date=row.get("transaction_date"),
            description=row.get("description"),
            reference=row.get("reference")
        ).first()
        
        if existing:
            continue
        
        statement = BankStatement(
            account_id=account_id,
            statement_date=date.today(),
            transaction_date=row.get("transaction_date"),
            description=row.get("description"),
            reference=row.get("reference"),
            debit=row.get("debit", 0.0),
            credit=row.get("credit", 0.0),
            balance=row.get("balance", 0.0)
        )
        db.session.add(statement)
        imported_count += 1
    
    db.session.commit()
    return True, f"Imported {imported_count} statements"


def get_unreconciled_statements(account_id):
    """Get unreconciled bank statements."""
    statements = BankStatement.query.filter_by(
        account_id=account_id,
        is_reconciled=False
    ).order_by(BankStatement.transaction_date).all()
    
    return [{
        "id": s.id,
        "date": s.transaction_date.isoformat(),
        "description": s.description,
        "reference": s.reference,
        "debit": s.debit,
        "credit": s.credit,
        "balance": s.balance
    } for s in statements]


def get_unmatched_ledger_entries(account_id, start_date, end_date):
    """Get ledger entries for a bank account that are not reconciled."""
    # Find the ledger for this bank account
    ledger = Ledger.query.filter(
        Ledger.name.like(f"%{BankAccount.query.get(account_id).account_name}%")
    ).first()
    
    if not ledger:
        return []
    
    entries = LedgerEntry.query.filter(
        LedgerEntry.ledger_id == ledger.id,
        LedgerEntry.entry_date.between(start_date, end_date)
    ).order_by(LedgerEntry.entry_date).all()
    
    return [{
        "id": e.id,
        "date": e.entry_date.isoformat(),
        "narration": e.narration,
        "debit": e.debit,
        "credit": e.credit,
        "voucher_no": e.voucher.voucher_no if e.voucher else ""
    } for e in entries]


def reconcile_statement(account_id, statement_id, ledger_entry_id):
    """Match a bank statement with a ledger entry."""
    statement = BankStatement.query.get(statement_id)
    entry = LedgerEntry.query.get(ledger_entry_id)
    
    if not statement or not entry:
        return False, "Statement or entry not found"
    
    # Verify amounts match
    statement_amount = statement.debit or statement.credit
    entry_amount = entry.debit or entry.credit
    
    if abs(statement_amount - entry_amount) > 0.01:  # Allow 0.01 rounding difference
        return False, f"Amounts don't match: {statement_amount} vs {entry_amount}"
    
    statement.is_reconciled = True
    statement.reconciled_with_id = ledger_entry_id
    db.session.commit()
    
    return True, "Reconciled successfully"


def create_reconciliation_session(account_id, bank_statement_date, bank_closing_balance, user_id):
    """Create a bank reconciliation session."""
    # Calculate book closing balance
    account = BankAccount.query.get(account_id)
    
    # Get all ledger entries for this account up to the statement date
    ledger = Ledger.query.filter(
        Ledger.name.like(f"%{account.account_name}%")
    ).first()
    
    book_balance = account.opening_balance
    if ledger:
        entries = LedgerEntry.query.filter(
            LedgerEntry.ledger_id == ledger.id,
            LedgerEntry.entry_date <= bank_statement_date
        ).all()
        
        for entry in entries:
            book_balance += (entry.debit or 0) - (entry.credit or 0)
    
    reconciliation = BankReconciliation(
        account_id=account_id,
        bank_statement_date=bank_statement_date,
        bank_closing_balance=bank_closing_balance,
        book_closing_balance=book_balance,
        difference=bank_closing_balance - book_balance,
        created_by=user_id
    )
    
    db.session.add(reconciliation)
    db.session.commit()
    
    return reconciliation


def get_reconciliation_report(account_id, statement_date):
    """Generate reconciliation report."""
    account = BankAccount.query.get(account_id)
    reconciliation = BankReconciliation.query.filter_by(
        account_id=account_id,
        bank_statement_date=statement_date
    ).first()
    
    if not reconciliation:
        return None
    
    # Get outstanding cheques
    outstanding_cheques = OutstandingCheck.query.filter(
        OutstandingCheck.account_id == account_id,
        OutstandingCheck.status == "outstanding",
        OutstandingCheck.issued_date <= statement_date
    ).all()
    
    # Get deposits in transit
    deposits_in_transit = DepositInTransit.query.filter(
        DepositInTransit.account_id == account_id,
        DepositInTransit.status == "pending",
        DepositInTransit.deposit_date <= statement_date
    ).all()
    
    # Get bank charges
    bank_charges = BankCharge.query.filter(
        BankCharge.account_id == account_id,
        BankCharge.charge_date <= statement_date,
        BankCharge.is_posted == False
    ).all()
    
    report = {
        "account": {
            "name": account.account_name,
            "number": account.account_number,
            "bank": account.bank_name
        },
        "statement_date": statement_date.isoformat(),
        "bank_balance": reconciliation.bank_closing_balance,
        "book_balance": reconciliation.book_closing_balance,
        "difference": reconciliation.difference,
        "reconciled": reconciliation.status == "reconciled",
        "adjustments": {
            "outstanding_cheques": [{
                "cheque_no": c.cheque_number,
                "date": c.cheque_date.isoformat(),
                "amount": c.amount,
                "payee": c.payee
            } for c in outstanding_cheques],
            "deposits_in_transit": [{
                "date": d.deposit_date.isoformat(),
                "amount": d.amount,
                "description": d.description
            } for d in deposits_in_transit],
            "bank_charges": [{
                "date": b.charge_date.isoformat(),
                "description": b.description,
                "amount": b.amount
            } for b in bank_charges]
        }
    }
    
    # Calculate adjusted balance
    total_outstanding = sum(c.amount for c in outstanding_cheques)
    total_deposits = sum(d.amount for d in deposits_in_transit)
    total_charges = sum(b.amount for b in bank_charges)
    
    adjusted_bank_balance = reconciliation.bank_closing_balance - total_outstanding + total_deposits
    adjusted_book_balance = reconciliation.book_closing_balance - total_charges
    
    report["adjusted_bank_balance"] = adjusted_bank_balance
    report["adjusted_book_balance"] = adjusted_book_balance
    report["final_difference"] = adjusted_bank_balance - adjusted_book_balance
    
    return report


def record_outstanding_check(account_id, cheque_number, cheque_date, amount, payee, voucher_id=None):
    """Record an outstanding cheque."""
    check = OutstandingCheck(
        account_id=account_id,
        cheque_number=cheque_number,
        cheque_date=cheque_date,
        amount=amount,
        payee=payee,
        voucher_id=voucher_id
    )
    db.session.add(check)
    db.session.commit()
    return check


def record_deposit_in_transit(account_id, deposit_date, amount, description, voucher_id=None):
    """Record a deposit not yet credited."""
    deposit = DepositInTransit(
        account_id=account_id,
        deposit_date=deposit_date,
        amount=amount,
        description=description,
        voucher_id=voucher_id
    )
    db.session.add(deposit)
    db.session.commit()
    return deposit


def record_bank_charge(account_id, charge_date, description, amount):
    """Record a bank charge."""
    charge = BankCharge(
        account_id=account_id,
        charge_date=charge_date,
        description=description,
        amount=amount
    )
    db.session.add(charge)
    db.session.commit()
    return charge


def clear_outstanding_check(check_id, cleared_date=None):
    """Mark a cheque as cleared."""
    check = OutstandingCheck.query.get(check_id)
    if check:
        check.status = "cleared"
        check.cleared_date = cleared_date or date.today()
        db.session.commit()
        return True
    return False


def clear_deposit_in_transit(deposit_id, credited_date=None):
    """Mark a deposit as credited."""
    deposit = DepositInTransit.query.get(deposit_id)
    if deposit:
        deposit.status = "credited"
        deposit.credited_date = credited_date or date.today()
        db.session.commit()
        return True
    return False
