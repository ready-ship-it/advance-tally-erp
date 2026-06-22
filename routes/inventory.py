from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import or_
from extensions import db
from models import Product, Category, Party
from services.hsn_service import lookup_hsn
from utils import login_required_full, admin_required

bp = Blueprint("inventory", __name__)


# ---------- Categories ----------
@bp.route("/categories")
@login_required_full
def categories():
    cats = Category.query.order_by(Category.name).all()
    return render_template("categories.html", categories=cats)


@bp.route("/categories/new", methods=["POST"])
@admin_required
def new_category():
    name = request.form.get("name", "").strip()
    hsn = request.form.get("default_hsn", "").strip()
    gst = float(request.form.get("default_gst_rate", 18) or 18)
    if name:
        db.session.add(Category(name=name, default_hsn=hsn, default_gst_rate=gst))
        db.session.commit()
        flash("Category added", "success")
    return redirect(url_for("inventory.categories"))


# ---------- Products ----------
@bp.route("/products")
@login_required_full
def products():
    q = request.args.get("q", "").strip()
    query = Product.query
    if q:
        query = query.filter(or_(
            Product.name.ilike(f"%{q}%"),
            Product.sku.ilike(f"%{q}%"),
            Product.barcode == q,
            Product.hsn_code == q,
        ))
    items = query.order_by(Product.name).limit(500).all()
    cats = Category.query.order_by(Category.name).all()
    return render_template("products.html", products=items, categories=cats, q=q)


@bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def new_product():
    if request.method == "POST":
        cat_id = request.form.get("category_id") or None
        hsn = request.form.get("hsn_code", "").strip()
        gst = float(request.form.get("gst_rate", 18) or 18)
        if not hsn and cat_id:
            c = Category.query.get(int(cat_id))
            if c:
                hsn = c.default_hsn or hsn
                gst = c.default_gst_rate or gst
        p = Product(
            sku=request.form["sku"].strip(),
            barcode=(request.form.get("barcode") or None) or None,
            name=request.form["name"].strip(),
            description=request.form.get("description", ""),
            category_id=int(cat_id) if cat_id else None,
            hsn_code=hsn,
            gst_rate=gst,
            unit=request.form.get("unit", "PCS"),
            purchase_price=float(request.form.get("purchase_price", 0) or 0),
            sale_price=float(request.form.get("sale_price", 0) or 0),
            stock_qty=float(request.form.get("stock_qty", 0) or 0),
            reorder_level=float(request.form.get("reorder_level", 0) or 0),
        )
        db.session.add(p)
        db.session.commit()
        flash("Product created", "success")
        return redirect(url_for("inventory.products"))
    cats = Category.query.order_by(Category.name).all()
    return render_template("product_form.html", product=None, categories=cats)


@bp.route("/products/<int:pid>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(pid):
    p = Product.query.get_or_404(pid)
    if request.method == "POST":
        p.sku = request.form["sku"].strip()
        p.barcode = (request.form.get("barcode") or None) or None
        p.name = request.form["name"].strip()
        p.description = request.form.get("description", "")
        cat_id = request.form.get("category_id") or None
        p.category_id = int(cat_id) if cat_id else None
        p.hsn_code = request.form.get("hsn_code", "").strip()
        p.gst_rate = float(request.form.get("gst_rate", 18) or 18)
        p.unit = request.form.get("unit", "PCS")
        p.purchase_price = float(request.form.get("purchase_price", 0) or 0)
        p.sale_price = float(request.form.get("sale_price", 0) or 0)
        p.stock_qty = float(request.form.get("stock_qty", 0) or 0)
        p.reorder_level = float(request.form.get("reorder_level", 0) or 0)
        p.is_active = bool(request.form.get("is_active"))
        db.session.commit()
        flash("Product updated", "success")
        return redirect(url_for("inventory.products"))
    cats = Category.query.order_by(Category.name).all()
    return render_template("product_form.html", product=p, categories=cats)


@bp.route("/products/lookup")
@login_required_full
def product_lookup():
    """Used by barcode scanner & sales screen."""
    code = request.args.get("code", "").strip()
    p = Product.query.filter(or_(Product.barcode == code, Product.sku == code)).first()
    if not p:
        return jsonify({"found": False})
    return jsonify({
        "found": True, "id": p.id, "name": p.name, "sku": p.sku,
        "hsn": p.hsn_code, "gst_rate": p.gst_rate,
        "sale_price": p.sale_price, "unit": p.unit, "stock": p.stock_qty,
    })


@bp.route("/hsn-lookup")
@login_required_full
def hsn_lookup():
    """Suggest HSN code by category name / product keyword."""
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify([])
    return jsonify(lookup_hsn(keyword))


# ---------- Parties ----------
@bp.route("/parties")
@login_required_full
def parties():
    items = Party.query.order_by(Party.name).all()
    return render_template("parties.html", parties=items)


@bp.route("/parties/new", methods=["GET", "POST"])
@admin_required
def new_party():
    if request.method == "POST":
        p = Party(
            name=request.form["name"].strip(),
            party_type=request.form.get("party_type", "customer"),
            gstin=request.form.get("gstin", "").strip(),
            state=request.form.get("state", "Maharashtra"),
            state_code=request.form.get("state_code", "27"),
            address=request.form.get("address", ""),
            phone=request.form.get("phone", ""),
            email=request.form.get("email", ""),
            opening_balance=float(request.form.get("opening_balance", 0) or 0),
        )
        db.session.add(p)
        db.session.commit()
        flash("Party added", "success")
        return redirect(url_for("inventory.parties"))
    return render_template("party_form.html", party=None)


@bp.route("/parties/<int:pid>/edit", methods=["GET", "POST"])
@admin_required
def edit_party(pid):
    p = Party.query.get_or_404(pid)
    if request.method == "POST":
        p.name = request.form["name"].strip()
        p.party_type = request.form.get("party_type", "customer")
        p.gstin = request.form.get("gstin", "").strip()
        p.state = request.form.get("state", "Maharashtra")
        p.state_code = request.form.get("state_code", "27")
        p.address = request.form.get("address", "")
        p.phone = request.form.get("phone", "")
        p.email = request.form.get("email", "")
        p.opening_balance = float(request.form.get("opening_balance", 0) or 0)
        db.session.commit()
        flash("Party updated", "success")
        return redirect(url_for("inventory.parties"))
    return render_template("party_form.html", party=p)


@bp.route("/retail-customers")
@login_required_full
def retail_customers():
    q = request.args.get("q", "").strip()
    query = Party.query.filter_by(party_type="customer")
    if q:
        query = query.filter(or_(
            Party.name.ilike(f"%{q}%"),
            Party.phone.ilike(f"%{q}%"),
            Party.email.ilike(f"%{q}%")
        ))
    items = query.order_by(Party.name).all()
    return render_template("retail_customers.html", customers=items, q=q)

