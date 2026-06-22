"""Tally XML import/export routes."""
from io import BytesIO
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from extensions import db
from models import Setting
from services.tally_service import (
    export_to_tally_xml, import_from_tally_xml,
    export_to_csv, import_from_csv
)
from utils import login_required_full, admin_required
from flask_login import current_user

bp = Blueprint("tally", __name__, url_prefix="/tally")


# ---------- Tally XML Export ----------
@bp.route("/export/xml")
@login_required_full
def export_xml():
    """Export data to Tally XML format."""
    fy_year = request.args.get("fy_year", type=int, default=2025)
    
    settings = {s.key: s.value for s in Setting.query.all()}
    company_name = settings.get("company_name", "My Company")
    
    xml_data = export_to_tally_xml(company_name, fy_year)
    
    return send_file(
        BytesIO(xml_data.encode()),
        as_attachment=True,
        download_name=f"Tally_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
        mimetype="application/xml"
    )


# ---------- Tally XML Import ----------
@bp.route("/import/xml", methods=["GET", "POST"])
@admin_required
def import_xml():
    """Import data from Tally XML file."""
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file provided", "error")
            return redirect(url_for("tally.import_xml"))
        
        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "error")
            return redirect(url_for("tally.import_xml"))
        
        if not file.filename.endswith(".xml"):
            flash("Only XML files are supported", "error")
            return redirect(url_for("tally.import_xml"))
        
        try:
            # Save file temporarily
            temp_path = f"/tmp/tally_import_{datetime.now().timestamp()}.xml"
            file.save(temp_path)
            
            # Import data
            imported = import_from_tally_xml(temp_path, current_user.id)
            
            message = f"Import successful: Categories: {imported['categories']}, Products: {imported['products']}, Parties: {imported['parties']}, Ledgers: {imported['ledgers']}"
            flash(message, "success")
            
            # Clean up
            import os
            os.remove(temp_path)
        
        except Exception as e:
            flash(f"Error importing file: {str(e)}", "error")
        
        return redirect(url_for("tally.import_xml"))
    
    return render_template("tally_import_xml.html")


# ---------- CSV Export ----------
@bp.route("/export/csv/<export_type>")
@login_required_full
def export_csv(export_type):
    """Export data to CSV format."""
    if export_type not in ["products", "parties", "vouchers"]:
        return jsonify({"error": "Invalid export type"}), 400
    
    csv_data = export_to_csv(export_type)
    
    return send_file(
        BytesIO(csv_data.encode()),
        as_attachment=True,
        download_name=f"{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mimetype="text/csv"
    )


# ---------- CSV Import ----------
@bp.route("/import/csv/<import_type>", methods=["GET", "POST"])
@admin_required
def import_csv(import_type):
    """Import data from CSV file."""
    if import_type not in ["products", "parties"]:
        flash("Invalid import type", "error")
        return redirect(url_for("tally.import_csv", import_type="products"))
    
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file provided", "error")
            return redirect(url_for("tally.import_csv", import_type=import_type))
        
        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "error")
            return redirect(url_for("tally.import_csv", import_type=import_type))
        
        if not file.filename.endswith(".csv"):
            flash("Only CSV files are supported", "error")
            return redirect(url_for("tally.import_csv", import_type=import_type))
        
        try:
            # Save file temporarily
            temp_path = f"/tmp/csv_import_{datetime.now().timestamp()}.csv"
            file.save(temp_path)
            
            # Import data
            imported, errors = import_from_csv(temp_path, import_type)
            
            if errors:
                error_msg = f"Imported {imported} records with {len(errors)} errors: " + "; ".join(errors[:5])
                flash(error_msg, "warning")
            else:
                flash(f"Successfully imported {imported} {import_type}", "success")
            
            # Clean up
            import os
            os.remove(temp_path)
        
        except Exception as e:
            flash(f"Error importing file: {str(e)}", "error")
        
        return redirect(url_for("tally.import_csv", import_type=import_type))
    
    return render_template("tally_import_csv.html", import_type=import_type)


# ---------- Migration Tools ----------
@bp.route("/migrate")
@admin_required
def migrate():
    """Data migration tools page."""
    return render_template("tally_migrate.html")


@bp.route("/sample-csv/<csv_type>")
@login_required_full
def sample_csv(csv_type):
    """Download sample CSV template."""
    if csv_type == "products":
        csv_content = """SKU,Name,Category,HSN Code,GST Rate,Unit,Purchase Price,Sale Price,Stock Qty,Reorder Level
PROD001,Product 1,Category 1,1234,18.0,PCS,100.00,150.00,10,5
PROD002,Product 2,Category 2,5678,5.0,KG,50.00,75.00,20,10"""
    
    elif csv_type == "parties":
        csv_content = """Name,Type,GSTIN,State,State Code,Address,Phone,Email,Opening Balance
Customer 1,customer,27AABCT1234H1Z0,Maharashtra,27,Address Line 1,9876543210,customer@example.com,0.00
Supplier 1,supplier,27AABCS5678H1Z0,Maharashtra,27,Supplier Address,9876543211,supplier@example.com,0.00"""
    
    else:
        return jsonify({"error": "Invalid CSV type"}), 400
    
    return send_file(
        BytesIO(csv_content.encode()),
        as_attachment=True,
        download_name=f"{csv_type}_template.csv",
        mimetype="text/csv"
    )


# ---------- API Endpoints ----------
@bp.route("/api/export-status")
@login_required_full
def api_export_status():
    """Get export status and available formats."""
    from models import Product, Party, Voucher
    
    return jsonify({
        "products_count": Product.query.count(),
        "parties_count": Party.query.count(),
        "vouchers_count": Voucher.query.filter_by(status="posted").count(),
        "formats": ["xml", "csv"],
        "export_types": ["products", "parties", "vouchers"]
    })


@bp.route("/api/import-history")
@login_required_full
def api_import_history():
    """Get import history (if tracking is implemented)."""
    return jsonify({
        "message": "Import history tracking can be implemented in future versions",
        "last_import": None
    })
