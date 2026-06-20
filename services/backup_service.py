"""Backup service.

Strategy: dump MySQL via mysqldump if available; otherwise fall back to a
SQLAlchemy logical dump (JSON of every table).

Schedule policy: auto every BACKUP_INTERVAL_HOURS (default 2). Users with
admin role can also trigger a manual one any time (e.g. "1-hour" cadence).
Retention: keep only last BACKUP_KEEP_LAST (default 5) backups.
"""
import os, gzip, json, shutil, subprocess, datetime as dt
from urllib.parse import urlparse
from flask import current_app
from extensions import db
from models import BackupLog
from config import Config

BACKUP_DIR = os.path.abspath(Config.BACKUP_DIR)
os.makedirs(BACKUP_DIR, exist_ok=True)


def _ts():
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def _mysql_parts():
    """Return dict(host, port, user, password, db) from SQLALCHEMY_DATABASE_URI."""
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    u = urlparse(uri.replace("mysql+pymysql://", "mysql://", 1))
    return {
        "host": u.hostname or "localhost", "port": str(u.port or 3306),
        "user": u.username or "root", "password": u.password or "",
        "db": (u.path or "").lstrip("/") or "tally_erp",
    }


def _dump_mysqldump(path):
    p = _mysql_parts()
    cmd = [
        "mysqldump", "-h", p["host"], "-P", p["port"], "-u", p["user"],
        f"-p{p['password']}", "--single-transaction", "--routines",
        "--triggers", "--databases", p["db"],
    ]
    with gzip.open(path, "wb") as gz:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        gz.write(proc.stdout)
    return os.path.getsize(path)


def _dump_logical(path):
    """Fallback: dump table contents to JSON.gz via SQLAlchemy reflection."""
    from sqlalchemy import MetaData
    meta = MetaData(); meta.reflect(bind=db.engine)
    dump = {"_version": 1, "tables": {}}
    with db.engine.connect() as conn:
        for tname, table in meta.tables.items():
            rows = []
            for r in conn.execute(table.select()).mappings():
                row = {}
                for k, v in dict(r).items():
                    if isinstance(v, (dt.date, dt.datetime)):
                        v = v.isoformat()
                    row[k] = v
                rows.append(row)
            dump["tables"][tname] = rows
    with gzip.open(path, "wt", encoding="utf-8") as gz:
        json.dump(dump, gz, default=str)
    return os.path.getsize(path)


def run_backup(mode: str = "auto"):
    """Create one backup file & enforce retention. Returns (filename, size)."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    use_sql = shutil.which("mysqldump") is not None
    ext = "sql.gz" if use_sql else "json.gz"
    fname = f"tally_backup_{_ts()}_{mode}.{ext}"
    path = os.path.join(BACKUP_DIR, fname)
    try:
        size = _dump_mysqldump(path) if use_sql else _dump_logical(path)
    except Exception:
        # Fallback to logical if mysqldump fails
        if use_sql:
            try: os.remove(path)
            except OSError: pass
            fname = f"tally_backup_{_ts()}_{mode}.json.gz"
            path = os.path.join(BACKUP_DIR, fname)
            size = _dump_logical(path)
        else:
            raise

    db.session.add(BackupLog(filename=fname, size_bytes=size, mode=mode))
    db.session.commit()

    _enforce_retention()
    return fname, size


def _enforce_retention():
    keep = Config.BACKUP_KEEP_LAST
    files = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith("tally_backup_")],
        reverse=True,
    )
    for old in files[keep:]:
        try: os.remove(os.path.join(BACKUP_DIR, old))
        except OSError: pass


def list_backups():
    if not os.path.isdir(BACKUP_DIR):
        return []
    out = []
    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if not f.startswith("tally_backup_"):
            continue
        full = os.path.join(BACKUP_DIR, f)
        st = os.stat(full)
        out.append({
            "name": f,
            "size_kb": st.st_size // 1024,
            "created": dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return out


def restore_from_file(path: str):
    """Restore from a *.sql.gz (mysqldump) or *.json.gz (logical) backup."""
    if path.endswith(".sql.gz"):
        p = _mysql_parts()
        cmd = ["mysql", "-h", p["host"], "-P", p["port"], "-u", p["user"], f"-p{p['password']}"]
        with gzip.open(path, "rb") as gz:
            subprocess.run(cmd, input=gz.read(), check=True)
    else:
        # logical restore: wipe tables & re-insert (skip _version key)
        from sqlalchemy import MetaData
        with gzip.open(path, "rt", encoding="utf-8") as gz:
            dump = json.load(gz)
        meta = MetaData(); meta.reflect(bind=db.engine)
        with db.engine.begin() as conn:
            for tname in reversed(list(meta.tables)):
                conn.execute(meta.tables[tname].delete())
            for tname, rows in dump.get("tables", {}).items():
                if tname in meta.tables and rows:
                    conn.execute(meta.tables[tname].insert(), rows)


# ---------- Scheduler ----------
def start_scheduler(app):
    """Register APScheduler job for auto backup every N hours."""
    from apscheduler.schedulers.background import BackgroundScheduler

    sched = BackgroundScheduler(daemon=True)

    def _job():
        with app.app_context():
            try:
                run_backup(mode="auto")
            except Exception as e:
                app.logger.exception("Auto backup failed: %s", e)

    sched.add_job(_job, "interval", hours=Config.BACKUP_INTERVAL_HOURS,
                  id="auto_backup", replace_existing=True)
    sched.start()
    app.extensions["backup_scheduler"] = sched
    return sched
