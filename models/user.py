from datetime import datetime
import bcrypt
from flask_login import UserMixin
from extensions import db

ROLE_MASTER = "master_admin"
ROLE_ADMIN = "admin"
ROLE_USER = "user"


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    full_name = db.Column(db.String(120))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default=ROLE_USER, nullable=False)
    is_active_flag = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), self.password_hash.encode())
        except Exception:
            return False

    @property
    def is_active(self):
        return self.is_active_flag

    def is_master(self): return self.role == ROLE_MASTER
    def is_admin(self): return self.role in (ROLE_MASTER, ROLE_ADMIN)
