"""HSN Master and lookup routes."""
from flask import Blueprint, render_template, request, jsonify, send_file
from io import BytesIO
from extensions import db
from models import HSNMaster
from services.hsn_service import (
    validate_hsn_code, search_hsn_by_code, search_hsn_by_description,
    get_hsn_suggestions, get_hsn_by_category, get_all_categories,
    get_hsn_detail, log_hsn_search, add_hsn_code, update_hsn_code,
    get_products_without_hsn, suggest_hsn_for_product, bulk_assign_hsn,
    export_hsn_master_csv, get_popular_searches
)
from utils import login_required_full, admin_required

bp = Blueprint("hsn", __name__, url_prefix="/hsn")


# ---------- HSN Master Management ----------
@bp.route("/master")
@login_required_full
def hsn_master():
    """View HSN Master table."""
    category = request.args.get("category")
    search = request.args.get("search", "").strip()
    
    query = HSNMaster.query.filter_by(is_active=True)
    
    if category:
        query = query.filter_by(category=category)
    
    if search:
        query = query.filter(
            db.or_(
                HSNMaster.hsn_code.ilike(f"%{search}%"),
                HSNMaster.description.ilike(f"%{search}%")
            )
        )
    
    hsn_codes = query.order_by(HSNMaster.hsn_code).all()
    categories = get_all_categories()
    
    return render_template("hsn_master.html", 
                          hsn_codes=hsn_codes, 
                          categories=categories,
                          selected_category=category,
                          search_term=search)


@bp.route("/master/new", methods=["GET", "POST"])
@admin_required
def add_hsn():
    """Add new HSN code."""
    if request.method == "POST":
        hsn_code = request.form.get("hsn_code", "").strip()
        description = request.form.get("description", "").strip()
        chapter = request.form.get("chapter", "").strip()
        category = request.form.get("category", "").strip()
        gst_rate = float(request.form.get("gst_rate", 18.0))
        cess_rate = float(request.form.get("cess_rate", 0.0))
        
        success, message = add_hsn_code(hsn_code, description, chapter, category, gst_rate, cess_rate)
        
        if success:
            from flask import flash, redirect, url_for
            flash(message, "success")
            return redirect(url_for("hsn.hsn_master"))
        else:
            from flask import flash
            flash(message, "error")
    
    categories = get_all_categories()
    return render_template("hsn_add.html", categories=categories)


@bp.route("/master/<hsn_code>/edit", methods=["GET", "POST"])
@admin_required
def edit_hsn(hsn_code):
    """Edit HSN code."""
    hsn = search_hsn_by_code(hsn_code)
    if not hsn:
        return jsonify({"error": "HSN code not found"}), 404
    
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        chapter = request.form.get("chapter", "").strip()
        category = request.form.get("category", "").strip()
        gst_rate = float(request.form.get("gst_rate", 18.0))
        cess_rate = float(request.form.get("cess_rate", 0.0))
        
        success, message = update_hsn_code(
            hsn_code,
            description=description,
            chapter=chapter,
            category=category,
            gst_rate=gst_rate,
            cess_rate=cess_rate
        )
        
        if success:
            from flask import flash, redirect, url_for
            flash(message, "success")
            return redirect(url_for("hsn.hsn_master"))
        else:
            from flask import flash
            flash(message, "error")
    
    categories = get_all_categories()
    return render_template("hsn_edit.html", hsn=hsn, categories=categories)


# ---------- HSN Lookup & Auto-suggest ----------
@bp.route("/api/suggest")
@login_required_full
def api_suggest():
    """API endpoint for HSN auto-suggest."""
    search_term = request.args.get("q", "").strip()
    
    if len(search_term) < 2:
        return jsonify([])
    
    suggestions = get_hsn_suggestions(search_term)
    
    # Log search
    log_hsn_search(search_term)
    
    return jsonify(suggestions)


@bp.route("/api/validate")
@login_required_full
def api_validate():
    """API endpoint for HSN code validation."""
    hsn_code = request.args.get("code", "").strip()
    
    is_valid, message = validate_hsn_code(hsn_code)
    
    if is_valid:
        # Get details
        detail = get_hsn_detail(hsn_code)
        return jsonify({
            "valid": True,
            "message": message,
            "detail": detail
        })
    else:
        return jsonify({
            "valid": False,
            "message": message
        })


@bp.route("/api/search")
@login_required_full
def api_search():
    """API endpoint for HSN search by description."""
    search_term = request.args.get("q", "").strip()
    
    if len(search_term) < 2:
        return jsonify([])
    
    results = search_hsn_by_description(search_term)
    
    data = [{
        "hsn_code": r.hsn_code,
        "description": r.description,
        "category": r.category,
        "gst_rate": r.gst_rate
    } for r in results]
    
    return jsonify(data)


@bp.route("/api/category/<category>")
@login_required_full
def api_category(category):
    """API endpoint to get HSN codes by category."""
    results = get_hsn_by_category(category)
    
    data = [{
        "hsn_code": r.hsn_code,
        "description": r.description,
        "gst_rate": r.gst_rate
    } for r in results]
    
    return jsonify(data)


@bp.route("/api/detail/<hsn_code>")
@login_required_full
def api_detail(hsn_code):
    """API endpoint to get HSN code details."""
    detail = get_hsn_detail(hsn_code)
    
    if detail:
        return jsonify(detail)
    else:
        return jsonify({"error": "HSN code not found"}), 404


# ---------- Product HSN Assignment ----------
@bp.route("/products/without-hsn")
@login_required_full
def products_without_hsn():
    """View products without HSN codes."""
    products = get_products_without_hsn()
    categories = get_all_categories()
    
    return render_template("hsn_products_without.html", 
                          products=products,
                          categories=categories)


@bp.route("/products/suggest-hsn")
@login_required_full
def suggest_hsn_for_products():
    """Suggest HSN codes for products."""
    from models import Product
    
    products = get_products_without_hsn()
    suggestions = {}
    
    for product in products:
        sugg = suggest_hsn_for_product(product.name)
        if sugg:
            suggestions[product.id] = sugg[0]
    
    return render_template("hsn_suggest.html", 
                          suggestions=suggestions,
                          products=products)


@bp.route("/api/bulk-assign", methods=["POST"])
@admin_required
def api_bulk_assign():
    """API endpoint for bulk HSN assignment."""
    data = request.get_json()
    product_ids = data.get("product_ids", [])
    hsn_code = data.get("hsn_code", "").strip()
    
    if not product_ids or not hsn_code:
        return jsonify({"error": "Missing product_ids or hsn_code"}), 400
    
    success, message = bulk_assign_hsn(product_ids, hsn_code)
    
    return jsonify({
        "success": success,
        "message": message
    })


# ---------- Reports & Export ----------
@bp.route("/export/csv")
@login_required_full
def export_csv():
    """Export HSN Master to CSV."""
    csv_data = export_hsn_master_csv()
    
    return send_file(
        BytesIO(csv_data.encode()),
        as_attachment=True,
        download_name="HSN_Master.csv",
        mimetype="text/csv"
    )


@bp.route("/popular-searches")
@login_required_full
def popular_searches():
    """View popular HSN searches."""
    searches = get_popular_searches(limit=20)
    
    return render_template("hsn_popular_searches.html", searches=searches)


@bp.route("/categories")
@login_required_full
def categories():
    """View all HSN categories."""
    categories = get_all_categories()
    
    category_data = []
    for cat in categories:
        count = HSNMaster.query.filter_by(category=cat, is_active=True).count()
        category_data.append({
            "name": cat,
            "count": count
        })
    
    return render_template("hsn_categories.html", categories=category_data)
