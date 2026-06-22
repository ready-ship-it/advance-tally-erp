"""Routes for product import from retailers and CSV."""
from flask import Blueprint, render_template, request, jsonify, send_file
from io import BytesIO
import csv
from extensions import db
from models import Product, Category
from services.product_scraper import (
    KhoslaElectronicsScraper, MDComputersScraper, VedantaComputersScraper,
    FlipkartScraper, AmazonScraper, import_products_from_scraper,
    import_sample_products
)
from utils import login_required_full, admin_required

bp = Blueprint("product_import", __name__, url_prefix="/products/import")


@bp.route("/")
@admin_required
def import_dashboard():
    """Product import dashboard."""
    return render_template("product_import_dashboard.html")


@bp.route("/sample")
@admin_required
def import_sample():
    """Import sample products for testing."""
    try:
        count = import_sample_products()
        return jsonify({
            "success": True,
            "message": f"Imported {count} sample products successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error importing sample products: {str(e)}"
        }), 400


@bp.route("/khosla", methods=["GET", "POST"])
@admin_required
def import_khosla():
    """Import products from Khosla Electronics."""
    if request.method == "POST":
        try:
            category_url = request.form.get("category_url", "")
            
            if not category_url:
                return jsonify({
                    "success": False,
                    "message": "Please provide a category URL"
                }), 400
            
            scraper = KhoslaElectronicsScraper()
            scraper.scrape_category(category_url)
            result = import_products_from_scraper(scraper, "Electronics")
            
            return jsonify({
                "success": True,
                "message": f"Imported {result['imported']} products from Khosla",
                "result": result
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error: {str(e)}"
            }), 400
    
    return render_template("product_import_retailer.html", retailer="Khosla Electronics")


@bp.route("/mdcomputers", methods=["GET", "POST"])
@admin_required
def import_mdcomputers():
    """Import products from MDComputers."""
    if request.method == "POST":
        try:
            category_url = request.form.get("category_url", "")
            
            if not category_url:
                return jsonify({
                    "success": False,
                    "message": "Please provide a category URL"
                }), 400
            
            scraper = MDComputersScraper()
            scraper.scrape_category(category_url)
            result = import_products_from_scraper(scraper, "Computers")
            
            return jsonify({
                "success": True,
                "message": f"Imported {result['imported']} products from MDComputers",
                "result": result
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error: {str(e)}"
            }), 400
    
    return render_template("product_import_retailer.html", retailer="MDComputers")


@bp.route("/vedanta", methods=["GET", "POST"])
@admin_required
def import_vedanta():
    """Import products from Vedanta Computers."""
    if request.method == "POST":
        try:
            category_url = request.form.get("category_url", "")
            
            if not category_url:
                return jsonify({
                    "success": False,
                    "message": "Please provide a category URL"
                }), 400
            
            scraper = VedantaComputersScraper()
            scraper.scrape_category(category_url)
            result = import_products_from_scraper(scraper, "Computers")
            
            return jsonify({
                "success": True,
                "message": f"Imported {result['imported']} products from Vedanta",
                "result": result
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error: {str(e)}"
            }), 400
    
    return render_template("product_import_retailer.html", retailer="Vedanta Computers")


@bp.route("/flipkart", methods=["GET", "POST"])
@admin_required
def import_flipkart():
    """Import products from Flipkart."""
    if request.method == "POST":
        try:
            category_url = request.form.get("category_url", "")
            
            if not category_url:
                return jsonify({
                    "success": False,
                    "message": "Please provide a category URL"
                }), 400
            
            scraper = FlipkartScraper()
            scraper.scrape_category(category_url)
            result = import_products_from_scraper(scraper, "Electronics")
            
            return jsonify({
                "success": True,
                "message": f"Imported {result['imported']} products from Flipkart",
                "result": result
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error: {str(e)}"
            }), 400
    
    return render_template("product_import_retailer.html", retailer="Flipkart")


@bp.route("/amazon", methods=["GET", "POST"])
@admin_required
def import_amazon():
    """Import products from Amazon."""
    if request.method == "POST":
        try:
            category_url = request.form.get("category_url", "")
            
            if not category_url:
                return jsonify({
                    "success": False,
                    "message": "Please provide a category URL"
                }), 400
            
            scraper = AmazonScraper()
            scraper.scrape_category(category_url)
            result = import_products_from_scraper(scraper, "Electronics")
            
            return jsonify({
                "success": True,
                "message": f"Imported {result['imported']} products from Amazon",
                "result": result
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error: {str(e)}"
            }), 400
    
    return render_template("product_import_retailer.html", retailer="Amazon")


@bp.route("/csv", methods=["GET", "POST"])
@admin_required
def import_csv():
    """Import products from CSV file."""
    if request.method == "POST":
        try:
            if "file" not in request.files:
                return jsonify({
                    "success": False,
                    "message": "No file provided"
                }), 400
            
            file = request.files["file"]
            if not file.filename.endswith(".csv"):
                return jsonify({
                    "success": False,
                    "message": "File must be CSV format"
                }), 400
            
            # Read CSV
            stream = file.stream.read().decode("UTF8")
            csv_data = csv.DictReader(stream.splitlines())
            
            imported = 0
            duplicates = 0
            errors = 0
            
            for row in csv_data:
                try:
                    # Get or create category
                    category_name = row.get("category", "General")
                    category = Category.query.filter_by(name=category_name).first()
                    if not category:
                        category = Category(name=category_name)
                        db.session.add(category)
                        db.session.commit()
                    
                    # Check if product exists
                    sku = row.get("sku", "").strip()
                    if not sku:
                        errors += 1
                        continue
                    
                    existing = Product.query.filter_by(sku=sku).first()
                    if existing:
                        duplicates += 1
                        continue
                    
                    # Create product
                    product = Product(
                        sku=sku,
                        name=row.get("name", ""),
                        category_id=category.id,
                        hsn_code=row.get("hsn_code", ""),
                        gst_rate=float(row.get("gst_rate", 18.0)),
                        unit=row.get("unit", "PCS"),
                        purchase_price=float(row.get("purchase_price", 0)),
                        sale_price=float(row.get("sale_price", 0)),
                        description=row.get("description", "")
                    )
                    
                    db.session.add(product)
                    imported += 1
                
                except Exception as e:
                    print(f"Error importing row: {str(e)}")
                    errors += 1
            
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": f"CSV import complete",
                "result": {
                    "imported": imported,
                    "duplicates": duplicates,
                    "errors": errors
                }
            })
        
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error: {str(e)}"
            }), 400
    
    return render_template("product_import_csv.html")


@bp.route("/template/csv")
@admin_required
def download_csv_template():
    """Download CSV template for product import."""
    output = BytesIO()
    writer = csv.DictWriter(output, fieldnames=[
        "sku", "name", "category", "hsn_code", "gst_rate", "unit",
        "purchase_price", "sale_price", "description"
    ])
    
    writer.writeheader()
    writer.writerow({
        "sku": "LAPTOP001",
        "name": "Dell Inspiron 15 Laptop",
        "category": "Computers",
        "hsn_code": "8471",
        "gst_rate": 18.0,
        "unit": "PCS",
        "purchase_price": 32000,
        "sale_price": 45000,
        "description": "15-inch Full HD Display"
    })
    
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="product_import_template.csv",
        mimetype="text/csv"
    )
