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
    from routes.warehouse import bp as warehouse_bp
    from routes.bank import bp as bank_bp
    from routes.tally import bp as tally_bp
    from routes.email import bp as email_bp
    from routes.hsn import bp as hsn_bp
    from routes.product_import import bp as product_import_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(inventory_bp, url_prefix="/inventory")
    app.register_blueprint(vouchers_bp, url_prefix="/vouchers")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(backup_bp, url_prefix="/backup")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(warehouse_bp)
    app.register_blueprint(bank_bp)
    app.register_blueprint(tally_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(hsn_bp)
    app.register_blueprint(product_import_bp)

    @app.route("/")
    def root():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        return redirect(url_for("dashboard.index"))

    @app.route("/migrate-db")
    def migrate_db():
        """One-time route to fix database schema."""
        try:
            from sqlalchemy import text
            # 1. Add transaction_id to vouchers if missing
            try:
                db.session.execute(text("ALTER TABLE vouchers ADD COLUMN transaction_id VARCHAR(100)"))
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                app.logger.info("Column transaction_id already exists or error: %s", e)

            # 2. Create any missing tables
            db.create_all()

            # 2b. Add missing bank account columns if needed
            try:
                db.session.execute(text("ALTER TABLE bank_accounts ADD COLUMN opening_balance FLOAT DEFAULT 0.0"))
                db.session.commit()
            except:
                db.session.rollback()

            # 3. Seed HSN data if empty
            from models.hsn import HSNMaster
            if not HSNMaster.query.first():
                from services.hsn_service import seed_hsn_master
                seed_hsn_master()
            
            return "<h1>Database Migration Successful!</h1><p>The transaction_id column has been added and tables are up to date.</p><a href='/'>Go to Dashboard</a>"
        except Exception as e:
            return f"<h1>Migration Failed</h1><p>Error: {str(e)}</p><a href='/'>Go to Dashboard</a>"

    @app.errorhandler(403)
    def forbidden(e):
        return ("<h1>403 — Forbidden</h1><p>You do not have permission for this action.</p>"
                "<a href='/'>Home</a>", 403)

    # ---- Auto-create tables + seed (idempotent) ----
    with app.app_context():
        try:
            from sqlalchemy import text
            # 1. Ensure new columns exist in existing tables
            try:
                db.session.execute(text("ALTER TABLE vouchers ADD COLUMN transaction_id VARCHAR(100)"))
                db.session.commit()
            except:
                db.session.rollback()

            try:
                db.session.execute(text("ALTER TABLE bank_accounts ADD COLUMN opening_balance FLOAT DEFAULT 0.0"))
                db.session.commit()
            except:
                db.session.rollback()

            # 2. Create all tables
            db.create_all()

            # 3. Seed HSN data if empty
            from models.hsn import HSNMaster
            if not HSNMaster.query.first():
                from services.hsn_service import seed_hsn_master
                seed_hsn_master()

            # 4. Seed other data
            from data.seed_products import seed_all
            seed_all()
        except Exception as e:
            app.logger.warning("DB init/seed skipped or partially failed: %s", e)

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
