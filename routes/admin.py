from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models import User, ROLE_MASTER, ROLE_ADMIN, ROLE_USER, Setting
from utils import master_required, admin_required

bp = Blueprint("admin", __name__)


@bp.route("/users")
@master_required
def users():
    items = User.query.order_by(User.id).all()
    return render_template("users.html", users=items, roles=[ROLE_MASTER, ROLE_ADMIN, ROLE_USER])


@bp.route("/users/new", methods=["POST"])
@master_required
def new_user():
    u = User(
        username=request.form["username"].strip(),
        email=request.form.get("email", "").strip() or None,
        full_name=request.form.get("full_name", "").strip(),
        role=request.form.get("role", ROLE_USER),
    )
    u.set_password(request.form["password"])
    db.session.add(u); db.session.commit()
    flash("User created", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:uid>/update", methods=["POST"])
@master_required
def update_user(uid):
    u = User.query.get_or_404(uid)
    u.role = request.form.get("role", u.role)
    u.is_active_flag = bool(request.form.get("is_active_flag"))
    u.full_name = request.form.get("full_name", u.full_name)
    if request.form.get("password"):
        u.set_password(request.form["password"])
    db.session.commit()
    flash("User updated", "success")
    return redirect(url_for("admin.users"))


@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    keys = ["company_name", "company_address", "company_gstin", "company_state",
            "company_state_code", "ftp_enabled_note"]
    if request.method == "POST":
        for k in keys:
            v = request.form.get(k, "")
            s = Setting.query.get(k) or Setting(key=k)
            s.value = v
            db.session.merge(s)
        db.session.commit()
        flash("Settings saved", "success")
        return redirect(url_for("admin.settings"))
    data = {s.key: s.value for s in Setting.query.all()}
    return render_template("settings.html", data=data)
