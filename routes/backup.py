import os
from flask import Blueprint, render_template, redirect, url_for, flash, send_from_directory, current_app, abort, request
from extensions import db
from models import BackupLog
from services.backup_service import run_backup, restore_from_file, list_backups
from services.ftp_service import upload_to_ftp
from utils import master_required, admin_required
from config import Config

bp = Blueprint("backup", __name__)


@bp.route("/")
@admin_required
def index():
    backups = list_backups()
    logs = BackupLog.query.order_by(BackupLog.id.desc()).limit(20).all()
    ftp_configured = bool(Config.FTP_HOST and Config.FTP_USER)
    return render_template("backup.html", backups=backups, logs=logs, ftp_configured=ftp_configured)


@bp.route("/run", methods=["POST"])
@admin_required
def run():
    mode = request.form.get("mode", "manual")
    fname, size = run_backup(mode=mode)
    flash(f"Backup created: {fname} ({size//1024} KB)", "success")
    return redirect(url_for("backup.index"))


@bp.route("/download/<path:fname>")
@master_required
def download(fname):
    safe = os.path.basename(fname)
    return send_from_directory(Config.BACKUP_DIR, safe, as_attachment=True)


@bp.route("/restore", methods=["POST"])
@master_required
def restore():
    fname = request.form.get("filename", "")
    safe = os.path.basename(fname)
    path = os.path.join(Config.BACKUP_DIR, safe)
    if not os.path.exists(path):
        flash("Backup file not found", "danger"); return redirect(url_for("backup.index"))
    restore_from_file(path)
    flash(f"Database restored from {safe}", "success")
    return redirect(url_for("backup.index"))


@bp.route("/upload-ftp", methods=["POST"])
@admin_required
def upload_ftp():
    fname = request.form.get("filename", "")
    safe = os.path.basename(fname)
    path = os.path.join(Config.BACKUP_DIR, safe)
    if not os.path.exists(path):
        flash("Backup file not found", "danger"); return redirect(url_for("backup.index"))
    ok, msg = upload_to_ftp(path)
    log = BackupLog.query.filter_by(filename=safe).order_by(BackupLog.id.desc()).first()
    if log:
        log.ftp_uploaded = ok; log.ftp_message = msg
        db.session.commit()
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("backup.index"))


@bp.route("/delete/<path:fname>", methods=["POST"])
@master_required
def delete(fname):
    safe = os.path.basename(fname)
    path = os.path.join(Config.BACKUP_DIR, safe)
    if os.path.exists(path):
        os.remove(path)
        flash("Backup deleted", "info")
    return redirect(url_for("backup.index"))
