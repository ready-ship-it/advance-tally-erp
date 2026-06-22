"""Email service for sending invoices and notifications."""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from io import BytesIO
from datetime import datetime
from extensions import db
from models import Setting, Voucher
from services.export_service import invoice_to_pdf
from num_to_words import number_to_words_indian


class EmailConfig:
    """Email configuration from settings."""
    
    @staticmethod
    def get_config():
        """Get email configuration from database settings."""
        settings = {s.key: s.value for s in Setting.query.all()}
        
        return {
            "smtp_server": settings.get("email_smtp_server", os.getenv("SMTP_SERVER", "smtp.gmail.com")),
            "smtp_port": int(settings.get("email_smtp_port", os.getenv("SMTP_PORT", 587))),
            "sender_email": settings.get("email_sender", os.getenv("SENDER_EMAIL", "")),
            "sender_password": settings.get("email_password", os.getenv("SENDER_PASSWORD", "")),
            "sender_name": settings.get("company_name", "Invoice System"),
            "use_tls": settings.get("email_use_tls", "true").lower() == "true"
        }


def send_invoice_email(voucher_id, recipient_email=None, subject=None, message=None, cc=None, bcc=None):
    """
    Send invoice via email.
    
    Args:
        voucher_id: Voucher ID to send
        recipient_email: Email address (uses party email if not provided)
        subject: Email subject
        message: Email body message
        cc: List of CC email addresses
        bcc: List of BCC email addresses
    
    Returns:
        (success, message)
    """
    voucher = Voucher.query.get(voucher_id)
    if not voucher:
        return False, "Voucher not found"
    
    # Get recipient email
    if not recipient_email:
        if not voucher.party or not voucher.party.email:
            return False, "No email address found for party"
        recipient_email = voucher.party.email
    
    # Validate email
    if not recipient_email or "@" not in recipient_email:
        return False, "Invalid email address"
    
    try:
        config = EmailConfig.get_config()
        
        if not config["sender_email"] or not config["sender_password"]:
            return False, "Email configuration not set. Please configure SMTP settings in admin panel."
        
        # Create email
        msg = MIMEMultipart()
        msg["From"] = f"{config['sender_name']} <{config['sender_email']}>"
        msg["To"] = recipient_email
        
        if cc:
            msg["Cc"] = ", ".join(cc)
        
        # Default subject and message
        if not subject:
            subject = f"Invoice {voucher.voucher_no} - {config['sender_name']}"
        
        if not message:
            message = f"""Dear {voucher.party.name if voucher.party else 'Valued Customer'},

Please find attached your invoice {voucher.voucher_no} dated {voucher.voucher_date.strftime('%d-%m-%Y')}.

Invoice Details:
- Invoice Number: {voucher.voucher_no}
- Date: {voucher.voucher_date.strftime('%d-%m-%Y')}
- Amount: ₹{voucher.grand_total:,.2f}
- Amount in Words: {number_to_words_indian(voucher.grand_total)}

Thank you for your business!

Best regards,
{config['sender_name']}"""
        
        msg["Subject"] = subject
        
        # Add message body
        msg.attach(MIMEText(message, "plain"))
        
        # Generate and attach PDF
        settings = {s.key: s.value for s in Setting.query.all()}
        amt_words = number_to_words_indian(voucher.grand_total)
        pdf_buf = invoice_to_pdf(voucher, settings, amt_words)
        
        # Attach PDF
        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(pdf_buf.getvalue())
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f"attachment; filename= Invoice_{voucher.voucher_no}.pdf"
        )
        msg.attach(attachment)
        
        # Send email
        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            if config["use_tls"]:
                server.starttls()
            
            server.login(config["sender_email"], config["sender_password"])
            
            # Prepare recipient list
            recipients = [recipient_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            server.sendmail(config["sender_email"], recipients, msg.as_string())
        
        # Log email sent
        log_email_sent(voucher_id, recipient_email, subject)
        
        return True, f"Invoice sent successfully to {recipient_email}"
    
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed. Check email and password."
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        return False, f"Error sending email: {str(e)}"


def send_bulk_invoices(voucher_ids, subject=None, message=None):
    """Send invoices to multiple parties."""
    results = {
        "success": 0,
        "failed": 0,
        "errors": []
    }
    
    for vid in voucher_ids:
        success, msg = send_invoice_email(vid, subject=subject, message=message)
        if success:
            results["success"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(f"Voucher {vid}: {msg}")
    
    return results


def send_reminder_email(voucher_id, reminder_type="overdue"):
    """Send payment reminder email."""
    voucher = Voucher.query.get(voucher_id)
    if not voucher or not voucher.party or not voucher.party.email:
        return False, "Voucher or party email not found"
    
    if reminder_type == "overdue":
        subject = f"Payment Reminder - Invoice {voucher.voucher_no}"
        message = f"""Dear {voucher.party.name},

This is a friendly reminder that payment for invoice {voucher.voucher_no} is now overdue.

Invoice Details:
- Invoice Number: {voucher.voucher_no}
- Date: {voucher.voucher_date.strftime('%d-%m-%Y')}
- Amount Due: ₹{voucher.grand_total:,.2f}

Please arrange payment at your earliest convenience.

Thank you!"""
    
    elif reminder_type == "upcoming":
        subject = f"Upcoming Payment Due - Invoice {voucher.voucher_no}"
        message = f"""Dear {voucher.party.name},

This is a courtesy reminder that payment for invoice {voucher.voucher_no} is due soon.

Invoice Details:
- Invoice Number: {voucher.voucher_no}
- Date: {voucher.voucher_date.strftime('%d-%m-%Y')}
- Amount Due: ₹{voucher.grand_total:,.2f}

Please ensure timely payment.

Thank you!"""
    
    else:
        return False, "Invalid reminder type"
    
    return send_invoice_email(voucher_id, subject=subject, message=message)


def send_test_email(recipient_email):
    """Send test email to verify configuration."""
    try:
        config = EmailConfig.get_config()
        
        if not config["sender_email"] or not config["sender_password"]:
            return False, "Email configuration not set"
        
        msg = MIMEMultipart()
        msg["From"] = f"{config['sender_name']} <{config['sender_email']}>"
        msg["To"] = recipient_email
        msg["Subject"] = "Test Email from Invoice System"
        
        body = f"""This is a test email from {config['sender_name']}.

If you received this email, your SMTP configuration is working correctly.

Sent at: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"""
        
        msg.attach(MIMEText(body, "plain"))
        
        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            if config["use_tls"]:
                server.starttls()
            
            server.login(config["sender_email"], config["sender_password"])
            server.sendmail(config["sender_email"], [recipient_email], msg.as_string())
        
        return True, "Test email sent successfully"
    
    except Exception as e:
        return False, f"Error: {str(e)}"


def log_email_sent(voucher_id, recipient_email, subject):
    """Log email sent (for audit trail)."""
    # This can be extended to create an EmailLog model for tracking
    print(f"[EMAIL LOG] Voucher {voucher_id} sent to {recipient_email} - Subject: {subject}")


def get_email_template(template_type="invoice"):
    """Get email template."""
    templates = {
        "invoice": {
            "subject": "Invoice {invoice_no}",
            "body": """Dear {customer_name},

Please find attached your invoice {invoice_no} dated {invoice_date}.

Invoice Details:
- Invoice Number: {invoice_no}
- Date: {invoice_date}
- Amount: ₹{amount:,.2f}
- Amount in Words: {amount_words}

Thank you for your business!

Best regards,
{company_name}"""
        },
        "reminder_overdue": {
            "subject": "Payment Reminder - Invoice {invoice_no}",
            "body": """Dear {customer_name},

This is a friendly reminder that payment for invoice {invoice_no} is now overdue.

Invoice Details:
- Invoice Number: {invoice_no}
- Date: {invoice_date}
- Amount Due: ₹{amount:,.2f}

Please arrange payment at your earliest convenience.

Thank you!"""
        },
        "reminder_upcoming": {
            "subject": "Upcoming Payment Due - Invoice {invoice_no}",
            "body": """Dear {customer_name},

This is a courtesy reminder that payment for invoice {invoice_no} is due soon.

Invoice Details:
- Invoice Number: {invoice_no}
- Date: {invoice_date}
- Amount Due: ₹{amount:,.2f}

Please ensure timely payment.

Thank you!"""
        }
    }
    
    return templates.get(template_type, templates["invoice"])
