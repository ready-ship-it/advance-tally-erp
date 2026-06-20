from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User
from config import Config

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.select_year"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password) or not user.is_active_flag:
            flash("Invalid credentials or account disabled", "danger")
            return render_template("login.html")
        login_user(user)
        flash(f"Welcome, {user.full_name or user.username}", "success")
        return redirect(url_for("auth.select_year"))
    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    session.pop("fy_year", None)
    logout_user()
    return redirect(url_for("auth.login"))


@bp.route("/select-year", methods=["GET", "POST"])
@login_required
def select_year():
    current = date.today().year
    years = list(range(current, Config.MAX_YEAR + 1))
    if request.method == "POST":
        y = int(request.form.get("year", current))
        if y < current or y > Config.MAX_YEAR:
            flash("Invalid year", "danger")
            return render_template("select_year.html", years=years, current=current)
        session["fy_year"] = y
        flash(f"Working in FY {y}-{str(y+1)[2:]}", "info")
        return redirect(url_for("dashboard.index"))
    return render_template("select_year.html", years=years, current=current)
