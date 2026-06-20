import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-prod-please-use-long-random-string")

    # MySQL via Railway (Railway injects MYSQL_URL or DATABASE_URL)
    DB_URL = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")
    if DB_URL and DB_URL.startswith("mysql://"):
        DB_URL = DB_URL.replace("mysql://", "mysql+pymysql://", 1)

    SQLALCHEMY_DATABASE_URI = DB_URL or (
        f"mysql+pymysql://{os.getenv('DB_USER','root')}:{os.getenv('DB_PASSWORD','')}"
        f"@{os.getenv('DB_HOST','localhost')}:{os.getenv('DB_PORT','3306')}/{os.getenv('DB_NAME','tally_erp')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Backup
    BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
    BACKUP_INTERVAL_HOURS = int(os.getenv("BACKUP_INTERVAL_HOURS", "2"))
    BACKUP_KEEP_LAST = int(os.getenv("BACKUP_KEEP_LAST", "5"))

    # FTP (optional)
    FTP_HOST = os.getenv("FTP_HOST", "")
    FTP_USER = os.getenv("FTP_USER", "")
    FTP_PASSWORD = os.getenv("FTP_PASSWORD", "")
    FTP_REMOTE_DIR = os.getenv("FTP_REMOTE_DIR", "/")
    FTP_PORT = int(os.getenv("FTP_PORT", "21"))
    FTP_USE_TLS = os.getenv("FTP_USE_TLS", "false").lower() == "true"

    # Company / Year
    MIN_YEAR = 2020
    MAX_YEAR = 2030
