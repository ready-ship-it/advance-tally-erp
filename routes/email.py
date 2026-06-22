"""Email and invoice delivery routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models import Voucher, Setting
from services.email_service import (
    send_invoice_email, send_bulk_invoices, send_reminder_email,
    send_test_email, get_email_template
)
from utils import login_required_full, admin_required
from flask_login import current_user

bp = Blueprint("email", __name__, url_prefix="/email")


# ---------- Email Configuration ----------
@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def email_settings():
    """Configure email settings."""
    if request.method == "POST":
        settings_to_save = [
            "email_smtp_server",
            "email_smtp_port",
            "email_sender",
            "email_password",
            "email_use_tls"
        ]
        
        for key in settings_to_save:
            value = request.form.get(key, "")
            setting = Setting.query.get(key) or Setting(key=key)
            setting.value = value
            db.session.merge(setting)
        
        db.session.commit()
        flash("Email settings saved", "success")
        return redirect(url_for("email.email_settings"))
    
    settings = {s.key: s.value for s in Setting.query.all()}
    return render_template("email_settings.html", settings=settings)


@bp.route("/test", methods=["GET", "POST"])
@admin_required
def test_email():
    """Test email configuration."""
    if request.method == "POST":
        recipient_email = request.form.get("recipient_email", "").strip()
        
        if not recipient_email or "@" not in recipient_email:
            flash("Invalid email address", "error")
            return redirect(url_for("email.test_email"))
        
        success, message = send_test_email(recipient_email)
        
        if success:
            flash(message, "success")
        else:
            flash(message, "error")
        
        return redirect(url_for("email.test_email"))
    
    return render_template("email_test.html")


# ---------- Send Invoice Email ----------
@bp.route("/invoice/<int:vid>", methods=["GET", "POST"])
@login_required_full
def send_invoice(vid):
    """Send invoice via email."""
    voucher = Voucher.query.get_or_404(vid)
    
    if request.method == "POST":
        recipient_email = request.form.get("recipient_email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        cc_emails = request.form.get("cc", "").strip()
        bcc_emails = request.form.get("bcc", "").strip()
        
        # Parse CC and BCC
        cc = [e.strip() for e in cc_emails.split(",") if e.strip()] if cc_emails else None
        bcc = [e.strip() for e in bcc_emails.split(",") if e.strip()] if bcc_emails else None
        
        success, msg = send_invoice_email(
            vid,
            recipient_email=recipient_email or None,
            subject=subject or None,
            message=message or None,
            cc=cc,
            bcc=bcc
        )
        
        if success:
            flash(msg, "success")
            return redirect(url_for("vouchers.view", vid=vid))
        else:
            flash(msg, "error")
    
    # Pre-fill with party email
    recipient_email = voucher.party.email if voucher.party else ""
    
    # Get default template
    template = get_email_template("invoice")
    default_subject = template["subject"].format(invoice_no=voucher.voucher_no)
    
    return render_template("email_send_invoice.html", 
                          voucher=voucher, 
                          recipient_email=recipient_email,
                          default_subject=default_subject)


@bp.route("/invoice/<int:vid>/send-json", methods=["POST"])
@login_required_full
def send_invoice_json(vid):
    """Send invoice via email (JSON API)."""
    data = request.get_json()
    
    recipient_email = data.get("recipient_email", "").strip()
    subject = data.get("subject", "").strip()
    message = data.get("message", "").strip()
    cc = data.get("cc", [])
    bcc = data.get("bcc", [])
    
    success, msg = send_invoice_email(
        vid,
        recipient_email=recipient_email or None,
        subject=subject or None,
        message=message or None,
        cc=cc if cc else None,
        bcc=bcc if bcc else None
    )
    
    return jsonify({
        "success": success,
        "message": msg
    })


# ---------- Bulk Send ----------
@bp.route("/bulk-send", methods=["GET", "POST"])
@login_required_full
def bulk_send():
    """Send invoices to multiple parties."""
    if request.method == "POST":
        voucher_ids = request.form.getlist("voucher_ids", type=int)
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        
        if not voucher_ids:
            flash("No invoices selected", "error")
            return redirect(url_for("email.bulk_send"))
        
        results = send_bulk_invoices(
            voucher_ids,
            subject=subject or None,
            message=message or None
        )
        
        flash(f"Sent: {results['success']}, Failed: {results['failed']}", "info")
        
        if results["errors"]:
            for error in results["errors"][:5]:
                flash(error, "warning")
        
        return redirect(url_for("email.bulk_send"))
    
    # Get unpaid invoices
    vouchers = Voucher.query.filter_by(voucher_type="sales", status="posted").all()
    
    return render_template("email_bulk_send.html", vouchers=vouchers)


# ---------- Payment Reminders ----------
@bp.route("/reminder/<int:vid>/<reminder_type>", methods=["POST"])
@login_required_full
def send_reminder(vid, reminder_type):
    """Send payment reminder."""
    if reminder_type not in ["overdue", "upcoming"]:
        return jsonify({"error": "Invalid reminder type"}), 400
    
    success, message = send_reminder_email(vid, reminder_type)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
    
    return redirect(url_for("vouchers.view", vid=vid))


# ---------- Email Templates ----------
@bp.route("/templates")
@login_required_full
def email_templates():
    """View and manage email templates."""
    templates = {
        "invoice": get_email_template("invoice"),
        "reminder_overdue": get_email_template("reminder_overdue"),
        "reminder_upcoming": get_email_template("reminder_upcoming")
    }
    
    return render_template("email_templates.html", templates=templates)


@bp.route("/templates/<template_type>")
@login_required_full
def view_template(template_type):
    """View email template."""
    template = get_email_template(template_type)
    
    if not template:
        return jsonify({"error": "Template not found"}), 404
    
    return jsonify(template)


# ---------- Email History (if implemented) ----------
@bp.route("/history")
@login_required_full
def email_history():
    """View email sending history."""
    # This can be extended to show actual email logs
    return render_template("email_history.html", emails=[])


# ---------- API Endpoints ----------
@bp.route("/api/send-invoice", methods=["POST"])
@login_required_full
def api_send_invoice():
    """API endpoint to send invoice."""
    data = request.get_json()
    voucher_id = data.get("voucher_id")
    recipient_email = data.get("recipient_email")
    
    if not voucher_id:
        return jsonify({"error": "Voucher ID required"}), 400
    
    success, message = send_invoice_email(voucher_id, recipient_email)
    
    return jsonify({
        "success": success,
        "message": message
    })


@bp.route("/api/email-config")
@admin_required
def api_email_config():
    """Get email configuration status."""
    settings = {s.key: s.value for s in Setting.query.all()}
    
    configured = bool(settings.get("email_sender") and settings.get("email_password"))
    
    return jsonify({
        "configured": configured,
        "smtp_server": settings.get("email_smtp_server", "Not set"),
        "sender_email": settings.get("email_sender", "Not set"),
        "use_tls": settings.get("email_use_tls", "true") == "true"
    })
