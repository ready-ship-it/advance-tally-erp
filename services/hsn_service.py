"""
HSN lookup, validation, and management service.

Approach:
 1. Database-backed HSN Master with common codes seeded from CBIC official HSN schedule.
 2. Fast lookup with caching for frequently searched codes.
 3. Auto-suggest functionality for product entry.
 4. Validation for HSN code format (2, 4, 6, or 8 digits).
 5. Integration with Product model for bulk assignment.
"""
import json
import os
import re
from functools import lru_cache
from sqlalchemy import or_, func
from extensions import db
from models import HSNMaster, HSNSearchLog, Product

# Legacy JSON file support
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "hsn_codes.json")


@lru_cache(maxsize=1)
def _load_legacy_json() -> list:
    """Load legacy HSN codes from JSON file if it exists."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def validate_hsn_code(hsn_code):
    """
    Validate HSN code format.
    Valid formats: 2, 4, 6, or 8 digits.
    
    Returns: (is_valid, message)
    """
    if not hsn_code:
        return False, "HSN code is required"
    
    # Remove spaces and special characters
    hsn_clean = hsn_code.strip().replace(" ", "").replace("-", "")
    
    # Check if it's numeric
    if not hsn_clean.isdigit():
        return False, "HSN code must contain only digits"
    
    # Check valid lengths (2, 4, 6, or 8 digits)
    if len(hsn_clean) not in [2, 4, 6, 8]:
        return False, f"HSN code must be 2, 4, 6, or 8 digits. Got {len(hsn_clean)} digits"
    
    return True, "Valid HSN code format"


def search_hsn_by_code(hsn_code):
    """Search HSN master by code."""
    is_valid, msg = validate_hsn_code(hsn_code)
    if not is_valid:
        return None
    
    hsn_clean = hsn_code.strip().replace(" ", "").replace("-", "")
    
    # Try exact match first
    result = HSNMaster.query.filter_by(hsn_code=hsn_clean, is_active=True).first()
    
    # If not found, try prefix match (for shorter codes)
    if not result and len(hsn_clean) < 8:
        result = HSNMaster.query.filter(
            HSNMaster.hsn_code.startswith(hsn_clean),
            HSNMaster.is_active == True
        ).first()
    
    return result


def search_hsn_by_description(search_term):
    """
    Search HSN codes by product description.
    Returns list of matching HSN codes.
    """
    if not search_term or len(search_term) < 2:
        return []
    
    search_pattern = f"%{search_term}%"
    
    results = HSNMaster.query.filter(
        or_(
            HSNMaster.description.ilike(search_pattern),
            HSNMaster.category.ilike(search_pattern),
            HSNMaster.chapter.ilike(search_pattern)
        ),
        HSNMaster.is_active == True
    ).limit(10).all()
    
    return results


def get_hsn_suggestions(search_term):
    """
    Get HSN code suggestions as user types.
    Returns list of matching HSN codes with descriptions.
    """
    results = search_hsn_by_description(search_term)
    
    suggestions = []
    for hsn in results:
        suggestions.append({
            "hsn_code": hsn.hsn_code,
            "description": hsn.description,
            "category": hsn.category,
            "gst_rate": hsn.gst_rate,
            "cess_rate": hsn.cess_rate
        })
    
    return suggestions


def get_hsn_by_category(category):
    """Get all HSN codes in a specific category."""
    results = HSNMaster.query.filter_by(
        category=category,
        is_active=True
    ).order_by(HSNMaster.hsn_code).all()
    
    return results


def get_all_categories():
    """Get list of all HSN categories."""
    categories = db.session.query(
        HSNMaster.category
    ).filter_by(is_active=True).distinct().all()
    
    return [c[0] for c in categories if c[0]]


def get_hsn_detail(hsn_code):
    """Get complete details of an HSN code."""
    is_valid, msg = validate_hsn_code(hsn_code)
    if not is_valid:
        return None
    
    hsn_clean = hsn_code.strip().replace(" ", "").replace("-", "")
    hsn = HSNMaster.query.filter_by(hsn_code=hsn_clean, is_active=True).first()
    
    if hsn:
        return {
            "hsn_code": hsn.hsn_code,
            "description": hsn.description,
            "chapter": hsn.chapter,
            "category": hsn.category,
            "gst_rate": hsn.gst_rate,
            "cess_rate": hsn.cess_rate,
            "is_active": hsn.is_active
        }
    
    return None


def log_hsn_search(search_term, hsn_code_found=None, user_id=None):
    """Log HSN search for analytics."""
    log = HSNSearchLog(
        search_term=search_term,
        hsn_code_found=hsn_code_found,
        user_id=user_id
    )
    db.session.add(log)
    db.session.commit()


def get_popular_searches(limit=10):
    """Get most popular HSN searches."""
    results = db.session.query(
        HSNSearchLog.search_term,
        func.count(HSNSearchLog.id).label("count")
    ).group_by(HSNSearchLog.search_term).order_by(
        func.count(HSNSearchLog.id).desc()
    ).limit(limit).all()
    
    return results


def add_hsn_code(hsn_code, description, chapter, category, gst_rate, cess_rate=0.0):
    """Add a new HSN code to master."""
    is_valid, msg = validate_hsn_code(hsn_code)
    if not is_valid:
        return False, msg
    
    hsn_clean = hsn_code.strip().replace(" ", "").replace("-", "")
    
    # Check if already exists
    existing = HSNMaster.query.filter_by(hsn_code=hsn_clean).first()
    if existing:
        return False, f"HSN code {hsn_clean} already exists"
    
    hsn = HSNMaster(
        hsn_code=hsn_clean,
        description=description,
        chapter=chapter,
        category=category,
        gst_rate=gst_rate,
        cess_rate=cess_rate
    )
    
    db.session.add(hsn)
    db.session.commit()
    
    return True, f"HSN code {hsn_clean} added successfully"


def update_hsn_code(hsn_code, **kwargs):
    """Update an HSN code."""
    is_valid, msg = validate_hsn_code(hsn_code)
    if not is_valid:
        return False, msg
    
    hsn_clean = hsn_code.strip().replace(" ", "").replace("-", "")
    hsn = HSNMaster.query.filter_by(hsn_code=hsn_clean).first()
    
    if not hsn:
        return False, f"HSN code {hsn_clean} not found"
    
    # Update allowed fields
    allowed_fields = ["description", "chapter", "category", "gst_rate", "cess_rate", "is_active"]
    for key, value in kwargs.items():
        if key in allowed_fields:
            setattr(hsn, key, value)
    
    db.session.commit()
    return True, f"HSN code {hsn_clean} updated successfully"


def get_products_without_hsn():
    """Get products that don't have HSN codes assigned."""
    products = Product.query.filter(
        (Product.hsn_code == None) | (Product.hsn_code == "")
    ).all()
    
    return products


def suggest_hsn_for_product(product_name):
    """
    Suggest HSN code for a product based on name.
    Uses product name to search HSN descriptions.
    """
    suggestions = get_hsn_suggestions(product_name)
    return suggestions


def bulk_assign_hsn(product_ids, hsn_code):
    """Bulk assign HSN code to multiple products."""
    is_valid, msg = validate_hsn_code(hsn_code)
    if not is_valid:
        return False, msg
    
    hsn_clean = hsn_code.strip().replace(" ", "").replace("-", "")
    
    # Verify HSN exists
    hsn = HSNMaster.query.filter_by(hsn_code=hsn_clean).first()
    if not hsn:
        return False, f"HSN code {hsn_clean} not found in master"
    
    # Update products
    Product.query.filter(Product.id.in_(product_ids)).update(
        {"hsn_code": hsn_clean, "gst_rate": hsn.gst_rate},
        synchronize_session=False
    )
    
    db.session.commit()
    return True, f"Assigned HSN {hsn_clean} to {len(product_ids)} products"


def export_hsn_master_csv():
    """Export HSN Master to CSV format."""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "HSN Code", "Description", "Chapter", "Category", "GST Rate", "CESS Rate", "Active"
    ])
    
    writer.writeheader()
    
    for hsn in HSNMaster.query.filter_by(is_active=True).all():
        writer.writerow({
            "HSN Code": hsn.hsn_code,
            "Description": hsn.description,
            "Chapter": hsn.chapter,
            "Category": hsn.category,
            "GST Rate": hsn.gst_rate,
            "CESS Rate": hsn.cess_rate,
            "Active": "Yes" if hsn.is_active else "No"
        })
    
    output.seek(0)
    return output.getvalue()


# Legacy functions for backward compatibility
def lookup_hsn(keyword: str, limit: int = 10) -> list:
    """Legacy function - lookup HSN by keyword."""
    suggestions = get_hsn_suggestions(keyword)
    return suggestions[:limit]


def best_match(keyword: str) -> dict:
    """Legacy function - get best match for keyword."""
    result = suggest_hsn_for_product(keyword)
    return result[0] if result else None

315	def seed_hsn_master():
316	    """Seed HSN Master with common codes for electronics and computers."""
317	    common_codes = [
318	        {"hsn_code": "8471", "description": "Automatic data processing machines and units thereof (Computers/Laptops)", "chapter": "84", "category": "Computers", "gst_rate": 18.0},
319	        {"hsn_code": "8473", "description": "Parts and accessories of computers", "chapter": "84", "category": "Parts", "gst_rate": 18.0},
320	        {"hsn_code": "8501", "description": "Electric motors and generators", "chapter": "85", "category": "Machinery", "gst_rate": 18.0},
321	        {"hsn_code": "8415", "description": "Air-conditioning machines", "chapter": "84", "category": "Appliances", "gst_rate": 28.0},
322	        {"hsn_code": "8517", "description": "Telephone sets, including smartphones", "chapter": "85", "category": "Telecom", "gst_rate": 18.0},
323	        {"hsn_code": "8523", "description": "Discs, tapes, solid-state storage (SSD/Pendrives)", "chapter": "85", "category": "Storage", "gst_rate": 18.0},
324	        {"hsn_code": "8528", "description": "Monitors and projectors", "chapter": "85", "category": "Display", "gst_rate": 18.0},
325	        {"hsn_code": "8544", "description": "Insulated wire, cables", "chapter": "85", "category": "Cables", "gst_rate": 18.0},
326	        {"hsn_code": "8443", "description": "Printers, copying machines", "chapter": "84", "category": "Office", "gst_rate": 18.0},
327	        {"hsn_code": "8504", "description": "Electrical transformers, static converters (UPS/Adapters)", "chapter": "85", "category": "Power", "gst_rate": 18.0},
328	        {"hsn_code": "8518", "description": "Microphones, loudspeakers, headphones", "chapter": "85", "category": "Audio", "gst_rate": 18.0},
329	        {"hsn_code": "8525", "description": "Transmission apparatus for radio-broadcasting or television (Cameras)", "chapter": "85", "category": "Video", "gst_rate": 18.0},
330	        {"hsn_code": "8507", "description": "Electric accumulators (Batteries)", "chapter": "85", "category": "Power", "gst_rate": 28.0},
331	        {"hsn_code": "8414", "description": "Air or vacuum pumps, air or other gas compressors and fans", "chapter": "84", "category": "Appliances", "gst_rate": 18.0},
332	    ]
333	    
334	    for data in common_codes:
335	        if not HSNMaster.query.filter_by(hsn_code=data["hsn_code"]).first():
336	            hsn = HSNMaster(**data)
337	            db.session.add(hsn)
338	    
339	    db.session.commit()
340	    return True
341	
