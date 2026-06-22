"""Warehouse and stock management routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models.warehouse import Warehouse, WarehouseStock, StockMovement, StockBin
from models import Product
from services.warehouse_service import (
    create_warehouse, get_warehouse_stock, update_warehouse_stock,
    transfer_stock, get_warehouse_summary, get_stock_movement_history,
    create_bin, update_bin_stock, get_bin_contents, get_low_stock_items
)
from utils import login_required_full, admin_required
from flask_login import current_user

bp = Blueprint("warehouse", __name__, url_prefix="/warehouse")


# ---------- Warehouse Management ----------
@bp.route("/")
@login_required_full
def list_warehouses():
    """List all warehouses."""
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    return render_template("warehouse_list.html", warehouses=warehouses)


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def new_warehouse():
    """Create a new warehouse."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip()
        location = request.form.get("location", "").strip()
        
        if not name or not code:
            flash("Name and code are required", "error")
            return redirect(url_for("warehouse.new_warehouse"))
        
        existing = Warehouse.query.filter_by(code=code).first()
        if existing:
            flash("Warehouse code already exists", "error")
            return redirect(url_for("warehouse.new_warehouse"))
        
        warehouse = create_warehouse(name, code, location)
        flash(f"Warehouse '{name}' created successfully", "success")
        return redirect(url_for("warehouse.view_warehouse", wid=warehouse.id))
    
    return render_template("warehouse_form.html")


@bp.route("/<int:wid>")
@login_required_full
def view_warehouse(wid):
    """View warehouse details and stock."""
    warehouse = Warehouse.query.get_or_404(wid)
    summary = get_warehouse_summary(wid)
    low_stock = get_low_stock_items(wid)
    
    return render_template("warehouse_view.html", warehouse=warehouse, summary=summary, low_stock=low_stock)


@bp.route("/<int:wid>/edit", methods=["GET", "POST"])
@admin_required
def edit_warehouse(wid):
    """Edit warehouse details."""
    warehouse = Warehouse.query.get_or_404(wid)
    
    if request.method == "POST":
        warehouse.name = request.form.get("name", warehouse.name).strip()
        warehouse.location = request.form.get("location", warehouse.location).strip()
        warehouse.is_active = bool(request.form.get("is_active"))
        db.session.commit()
        flash("Warehouse updated", "success")
        return redirect(url_for("warehouse.view_warehouse", wid=wid))
    
    return render_template("warehouse_form.html", warehouse=warehouse)


# ---------- Stock Management ----------
@bp.route("/<int:wid>/stock/add", methods=["POST"])
@login_required_full
def add_stock(wid):
    """Add stock to warehouse."""
    warehouse = Warehouse.query.get_or_404(wid)
    product_id = request.form.get("product_id", type=int)
    quantity = request.form.get("quantity", type=float)
    reference = request.form.get("reference", "").strip()
    narration = request.form.get("narration", "").strip()
    
    if not product_id or not quantity or quantity <= 0:
        flash("Invalid product or quantity", "error")
        return redirect(url_for("warehouse.view_warehouse", wid=wid))
    
    product = Product.query.get_or_404(product_id)
    
    update_warehouse_stock(
        wid, product_id, quantity, "IN",
        reference=reference,
        narration=narration,
        user_id=current_user.id
    )
    
    flash(f"Added {quantity} {product.unit} of {product.name}", "success")
    return redirect(url_for("warehouse.view_warehouse", wid=wid))


@bp.route("/<int:wid>/stock/adjust", methods=["POST"])
@login_required_full
def adjust_stock(wid):
    """Adjust stock (inventory correction)."""
    warehouse = Warehouse.query.get_or_404(wid)
    product_id = request.form.get("product_id", type=int)
    quantity = request.form.get("quantity", type=float)
    narration = request.form.get("narration", "").strip()
    
    if not product_id or quantity is None:
        flash("Invalid product or quantity", "error")
        return redirect(url_for("warehouse.view_warehouse", wid=wid))
    
    product = Product.query.get_or_404(product_id)
    
    update_warehouse_stock(
        wid, product_id, quantity, "ADJUSTMENT",
        narration=narration,
        user_id=current_user.id
    )
    
    action = "Added" if quantity > 0 else "Removed"
    flash(f"{action} {abs(quantity)} {product.unit} of {product.name}", "success")
    return redirect(url_for("warehouse.view_warehouse", wid=wid))


@bp.route("/transfer", methods=["GET", "POST"])
@login_required_full
def transfer_stock_ui():
    """Transfer stock between warehouses."""
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    
    if request.method == "POST":
        from_wid = request.form.get("from_warehouse_id", type=int)
        to_wid = request.form.get("to_warehouse_id", type=int)
        product_id = request.form.get("product_id", type=int)
        quantity = request.form.get("quantity", type=float)
        reference = request.form.get("reference", "").strip()
        narration = request.form.get("narration", "").strip()
        
        if not all([from_wid, to_wid, product_id, quantity]) or quantity <= 0:
            flash("Invalid input", "error")
            return redirect(url_for("warehouse.transfer_stock_ui"))
        
        if from_wid == to_wid:
            flash("Source and destination warehouses must be different", "error")
            return redirect(url_for("warehouse.transfer_stock_ui"))
        
        product = Product.query.get_or_404(product_id)
        success, message = transfer_stock(from_wid, to_wid, product_id, quantity, reference, narration, current_user.id)
        
        if success:
            flash(f"Transferred {quantity} {product.unit} of {product.name}", "success")
        else:
            flash(message, "error")
        
        return redirect(url_for("warehouse.transfer_stock_ui"))
    
    return render_template("warehouse_transfer.html", warehouses=warehouses)


# ---------- Stock Movements ----------
@bp.route("/<int:wid>/movements")
@login_required_full
def stock_movements(wid):
    """View stock movement history."""
    warehouse = Warehouse.query.get_or_404(wid)
    movements = get_stock_movement_history(warehouse_id=wid)
    
    return render_template("warehouse_movements.html", warehouse=warehouse, movements=movements)


# ---------- Low Stock Alert ----------
@bp.route("/low-stock")
@login_required_full
def low_stock_alert():
    """View items below reorder level."""
    low_stock = get_low_stock_items()
    
    return render_template("warehouse_low_stock.html", items=low_stock)


# ---------- Bin Management (Optional) ----------
@bp.route("/<int:wid>/bins")
@login_required_full
def list_bins(wid):
    """List bins in a warehouse."""
    warehouse = Warehouse.query.get_or_404(wid)
    bins = StockBin.query.filter_by(warehouse_id=wid, is_active=True).all()
    
    return render_template("warehouse_bins.html", warehouse=warehouse, bins=bins)


@bp.route("/<int:wid>/bins/new", methods=["GET", "POST"])
@admin_required
def new_bin(wid):
    """Create a new bin."""
    warehouse = Warehouse.query.get_or_404(wid)
    
    if request.method == "POST":
        bin_code = request.form.get("bin_code", "").strip()
        location_description = request.form.get("location_description", "").strip()
        
        if not bin_code:
            flash("Bin code is required", "error")
            return redirect(url_for("warehouse.new_bin", wid=wid))
        
        existing = StockBin.query.filter_by(warehouse_id=wid, bin_code=bin_code).first()
        if existing:
            flash("Bin code already exists in this warehouse", "error")
            return redirect(url_for("warehouse.new_bin", wid=wid))
        
        bin = create_bin(wid, bin_code, location_description)
        flash(f"Bin '{bin_code}' created", "success")
        return redirect(url_for("warehouse.list_bins", wid=wid))
    
    return render_template("warehouse_bin_form.html", warehouse=warehouse)


# ---------- API Endpoints ----------
@bp.route("/api/stock/<int:wid>/<int:pid>")
@login_required_full
def api_get_stock(wid, pid):
    """Get stock for a product in a warehouse (API)."""
    stock = get_warehouse_stock(wid, pid)
    return jsonify({
        "warehouse_id": wid,
        "product_id": pid,
        "quantity": stock.quantity,
        "available": stock.available_qty,
        "reserved": stock.reserved_qty
    })


@bp.route("/api/warehouse/<int:wid>/summary")
@login_required_full
def api_warehouse_summary(wid):
    """Get warehouse summary (API)."""
    summary = get_warehouse_summary(wid)
    return jsonify(summary)


@bp.route("/api/low-stock")
@login_required_full
def api_low_stock():
    """Get low stock items (API)."""
    low_stock = get_low_stock_items()
    return jsonify({"items": low_stock})
