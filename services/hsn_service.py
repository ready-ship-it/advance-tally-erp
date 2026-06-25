"""HSN Lookup and Master data service."""
from extensions import db
from models.hsn import HSNMaster, HSNSearchLog
from models.product import Product
import csv
from io import StringIO
from datetime import datetime

def validate_hsn_code(code: str) -> tuple:
    """Validate HSN code length (2, 4, 6, or 8 digits)."""
    if not code:
        return False, "HSN code is required"
    if not code.isdigit():
        return False, "HSN code must contain only digits"
    if len(code) not in (2, 4, 6, 8):
        return False, "HSN code must be 2, 4, 6, or 8 digits"
    return True, "Valid HSN code"

def search_hsn_by_code(code: str) -> HSNMaster:
    """Find HSNMaster record by code."""
    return HSNMaster.query.filter_by(hsn_code=code, is_active=True).first()

def search_hsn_by_description(query: str, limit: int = 20) -> list:
    """Search HSNMaster by description."""
    return HSNMaster.query.filter(
        HSNMaster.description.ilike(f"%{query}%"),
        HSNMaster.is_active == True
    ).limit(limit).all()

def get_hsn_suggestions(query: str, limit: int = 10) -> list:
    """Get auto-suggest results for HSN (by code or description)."""
    results = HSNMaster.query.filter(
        db.or_(
            HSNMaster.hsn_code.ilike(f"%{query}%"),
            HSNMaster.description.ilike(f"%{query}%")
        ),
        HSNMaster.is_active == True
    ).limit(limit).all()
    
    return [{
        "hsn_code": r.hsn_code,
        "description": r.description,
        "gst_rate": r.gst_rate,
        "category": r.category
    } for r in results]

def get_hsn_by_category(category: str) -> list:
    """Get all HSN codes in a category."""
    return HSNMaster.query.filter_by(category=category, is_active=True).all()

def get_all_categories() -> list:
    """Get list of unique HSN categories."""
    results = db.session.query(HSNMaster.category).distinct().all()
    return [r[0] for r in results if r[0]]

def get_hsn_detail(code: str) -> dict:
    """Get full details of an HSN code."""
    hsn = search_hsn_by_code(code)
    if not hsn:
        return None
    return {
        "hsn_code": hsn.hsn_code,
        "description": hsn.description,
        "chapter": hsn.chapter,
        "category": hsn.category,
        "gst_rate": hsn.gst_rate,
        "cess_rate": hsn.cess_rate
    }

def log_hsn_search(term: str):
    """Log HSN search term for analytics."""
    log = HSNSearchLog.query.filter_by(search_term=term).first()
    if log:
        log.search_count += 1
        log.last_searched = datetime.utcnow()
    else:
        log = HSNSearchLog(search_term=term)
        db.session.add(log)
    db.session.commit()

def add_hsn_code(code, description, chapter, category, gst_rate=18.0, cess_rate=0.0):
    """Add new HSN code to master."""
    valid, msg = validate_hsn_code(code)
    if not valid:
        return False, msg
    
    if search_hsn_by_code(code):
        return False, "HSN code already exists"
    
    hsn = HSNMaster(
        hsn_code=code,
        description=description,
        chapter=chapter,
        category=category,
        gst_rate=gst_rate,
        cess_rate=cess_rate
    )
    db.session.add(hsn)
    db.session.commit()
    return True, f"HSN code {code} added successfully"

def update_hsn_code(code, **kwargs):
    """Update HSN code details."""
    hsn = search_hsn_by_code(code)
    if not hsn:
        return False, "HSN code not found"
    
    for key, value in kwargs.items():
        if hasattr(hsn, key):
            setattr(hsn, key, value)
    
    db.session.commit()
    return True, f"HSN code {code} updated successfully"

def get_products_without_hsn():
    """Find products missing HSN codes."""
    return Product.query.filter(
        db.or_(Product.hsn_code == None, Product.hsn_code == "")
    ).all()

def suggest_hsn_for_product(product_name: str):
    """Suggest HSN based on product name."""
    # Simple keyword match
    words = product_name.split()
    for word in words:
        if len(word) > 3:
            results = get_hsn_suggestions(word, limit=1)
            if results:
                return results
    return []

def bulk_assign_hsn(product_ids, hsn_code):
    """Assign HSN code to multiple products."""
    hsn = search_hsn_by_code(hsn_code)
    if not hsn:
        return False, "Invalid HSN code"
    
    products = Product.query.filter(Product.id.in_(product_ids)).all()
    for p in products:
        p.hsn_code = hsn_code
        p.gst_rate = hsn.gst_rate
    
    db.session.commit()
    return True, f"Assigned HSN {hsn_code} to {len(products)} products"

def export_hsn_master_csv():
    """Export HSN Master to CSV string."""
    hsn_codes = HSNMaster.query.all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["HSN Code", "Description", "Chapter", "Category", "GST Rate", "Cess Rate", "Active"])
    
    for h in hsn_codes:
        writer.writerow([
            h.hsn_code, h.description, h.chapter, h.category, 
            h.gst_rate, h.cess_rate, h.is_active
        ])
    
    return output.getvalue()

def get_popular_searches(limit=10):
    """Get popular HSN search terms."""
    return HSNSearchLog.query.order_by(HSNSearchLog.search_count.desc()).limit(limit).all()

# Legacy functions for backward compatibility
def lookup_hsn(keyword: str, limit: int = 10) -> list:
    """Legacy function - lookup HSN by keyword."""
    suggestions = get_hsn_suggestions(keyword)
    return suggestions[:limit]

def best_match(keyword: str) -> dict:
    """Legacy function - get best match for keyword."""
    result = suggest_hsn_for_product(keyword)
    return result[0] if result else None

def seed_hsn_master():
    """Seed HSN Master with common codes for electronics and computers."""
    common_codes = [
        {"hsn_code": "8471", "description": "Automatic data processing machines and units thereof (Computers/Laptops)", "chapter": "84", "category": "Computers", "gst_rate": 18.0},
        {"hsn_code": "8473", "description": "Parts and accessories of computers", "chapter": "84", "category": "Parts", "gst_rate": 18.0},
        {"hsn_code": "8501", "description": "Electric motors and generators", "chapter": "85", "category": "Machinery", "gst_rate": 18.0},
        {"hsn_code": "8415", "description": "Air-conditioning machines", "chapter": "84", "category": "Appliances", "gst_rate": 28.0},
        {"hsn_code": "8517", "description": "Telephone sets, including smartphones", "chapter": "85", "category": "Telecom", "gst_rate": 18.0},
        {"hsn_code": "8523", "description": "Discs, tapes, solid-state storage (SSD/Pendrives)", "chapter": "85", "category": "Storage", "gst_rate": 18.0},
        {"hsn_code": "8528", "description": "Monitors and projectors", "chapter": "85", "category": "Display", "gst_rate": 18.0},
        {"hsn_code": "8544", "description": "Insulated wire, cables", "chapter": "85", "category": "Cables", "gst_rate": 18.0},
        {"hsn_code": "8443", "description": "Printers, copying machines", "chapter": "84", "category": "Office", "gst_rate": 18.0},
        {"hsn_code": "8504", "description": "Electrical transformers, static converters (UPS/Adapters)", "chapter": "85", "category": "Power", "gst_rate": 18.0},
        {"hsn_code": "8518", "description": "Microphones, loudspeakers, headphones", "chapter": "85", "category": "Audio", "gst_rate": 18.0},
        {"hsn_code": "8525", "description": "Transmission apparatus for radio-broadcasting or television (Cameras)", "chapter": "85", "category": "Video", "gst_rate": 18.0},
        {"hsn_code": "8507", "description": "Electric accumulators (Batteries)", "chapter": "85", "category": "Power", "gst_rate": 28.0},
        {"hsn_code": "8414", "description": "Air or vacuum pumps, air or other gas compressors and fans", "chapter": "84", "category": "Appliances", "gst_rate": 18.0},
    ]
    
    for data in common_codes:
        if not HSNMaster.query.filter_by(hsn_code=data["hsn_code"]).first():
            hsn = HSNMaster(**data)
            db.session.add(hsn)
    
    db.session.commit()
    return True
