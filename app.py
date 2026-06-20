"""Tally-style ERP — Flask app entry point."""
import os
import logging
from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from config import Config
from extensions import db
from models import User

login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    logging.basicConfig(level=logging.INFO)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(uid):
        return db.session.get(User, int(uid))

    # ---- Blueprints ----
    from routes.auth import bp as auth_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.inventory import bp as inventory_bp
    from routes.vouchers import bp as vouchers_bp
    from routes.reports import bp as reports_bp
    from routes.backup import bp as backup_bp
    from routes.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(inventory_bp, url_prefix="/inventory")
    app.register_blueprint(vouchers_bp, url_prefix="/vouchers")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(backup_bp, url_prefix="/backup")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.route("/")
    def root():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        return redirect(url_for("dashboard.index"))

    @app.errorhandler(403)
    def forbidden(e):
        return ("<h1>403 — Forbidden</h1><p>You do not have permission for this action.</p>"
                "<a href='/'>Home</a>", 403)

    # ---- Auto-create tables + seed (idempotent) ----
    with app.app_context():
        try:
            db.create_all()
            from data.seed_products import seed_all
            seed_all()
        except Exception as e:
            app.logger.warning("DB init/seed skipped: %s", e)

    # ---- Backup scheduler (skip in test/CLI) ----
    if os.getenv("ENABLE_SCHEDULER", "true").lower() == "true":
        try:
            from services.backup_service import start_scheduler
            start_scheduler(app)
            app.logger.info("Backup scheduler started: every %sh, keep %s",
                            Config.BACKUP_INTERVAL_HOURS, Config.BACKUP_KEEP_LAST)
        except Exception as e:
            app.logger.warning("Scheduler not started: %s", e)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "0") == "1")
