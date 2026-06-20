from functools import wraps
from datetime import date
from flask import session, redirect, url_for, flash, abort
from flask_login import current_user


def login_required_full(fn):
    """Requires login AND a selected financial year."""
    @wraps(fn)
    def wrapper(*a, **kw):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not session.get("fy_year"):
            return redirect(url_for("auth.select_year"))
        return fn(*a, **kw)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin():
            abort(403)
        return fn(*a, **kw)
    return wrapper


def master_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_master():
            abort(403)
        return fn(*a, **kw)
    return wrapper


def current_fy():
    """Return selected FY year (int) e.g. 2025 means FY 2025-26."""
    return session.get("fy_year") or date.today().year


def fy_range(fy_year: int):
    """Indian FY runs Apr 1 -> Mar 31 of next year."""
    from datetime import date as d
    return d(fy_year, 4, 1), d(fy_year + 1, 3, 31)
