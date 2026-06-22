"""HSN (Harmonized System of Nomenclature) Master data model."""
from datetime import datetime
from extensions import db


class HSNMaster(db.Model):
    """HSN Master - Store common HSN codes with descriptions and GST rates."""
    __tablename__ = "hsn_master"
    
    id = db.Column(db.Integer, primary_key=True)
    hsn_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    description = db.Column(db.String(500), nullable=False)
    chapter = db.Column(db.String(50))  # e.g., "Chapter 84 - Machinery"
    category = db.Column(db.String(100))  # e.g., "Electronics", "Computers", "Appliances"
    gst_rate = db.Column(db.Float, default=18.0)  # GST rate percentage
    cess_rate = db.Column(db.Float, default=0.0)  # CESS rate (if applicable)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<HSNMaster {self.hsn_code}: {self.description}>"


class HSNSearchLog(db.Model):
    """Log HSN searches for analytics and popular searches."""
    __tablename__ = "hsn_search_log"
    
    id = db.Column(db.Integer, primary_key=True)
    search_term = db.Column(db.String(200), nullable=False)
    hsn_code_found = db.Column(db.String(20))
    user_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# HSN Master Data - Common codes for electronics and computers
HSN_MASTER_DATA = [
    # Chapter 84 - Machinery
    {
        "hsn_code": "8401",
        "description": "Boilers, machinery and mechanical appliances",
        "chapter": "Chapter 84",
        "category": "Machinery",
        "gst_rate": 18.0
    },
    
    # Chapter 85 - Electrical machinery
    {
        "hsn_code": "8501",
        "description": "Electric motors and generators (excluding generating sets)",
        "chapter": "Chapter 85",
        "category": "Electrical",
        "gst_rate": 18.0
    },
    {
        "hsn_code": "8415",
        "description": "Air-conditioning machines",
        "chapter": "Chapter 85",
        "category": "Appliances",
        "gst_rate": 28.0
    },
    {
        "hsn_code": "8471",
        "description": "Automatic data processing machines and units thereof; magnetic or optical readers",
        "chapter": "Chapter 85",
        "category": "Computers",
        "gst_rate": 18.0
    },
    {
        "hsn_code": "8472",
        "description": "Other office machines",
        "chapter": "Chapter 85",
        "category": "Office Equipment",
        "gst_rate": 18.0
    },
    {
        "hsn_code": "8473",
        "description": "Parts and accessories of machines of headings 8470 to 8472",
        "chapter": "Chapter 85",
        "category": "Computer Parts",
        "gst_rate": 18.0
    },
    {
        "hsn_code": "8504",
        "description": "Electrical transformers, static converters and inductors",
        "chapter": "Chapter 85",
        "category": "Electrical",
        "gst_rate": 18.0
    },
    {
        "hsn_code": "8517",
        "description": "Telephone sets, including smartphones and other voice/image/data transmission equipment",
        "chapter": "Chapter 85",
        "category": "Telecom",
        "gst_rate": 18.0
    },
    {
        "hsn_code": "8523",
        "description": "Discs, tapes, solid-state non-volatile storage devices, smart cards and other media",
        "chapter": "Chapter 85",
        "category": "Storage Devices",
        "gst_rate": 18.0
    },
    {
        "hsn_code": "8528",
        "description": "Monitors and projectors, reception apparatus for television",
        "chapter": "Chapter 85",
        "category": "Display",
        "gst_rate": 18.0
    },
    {
        "hsn_code": "8544",
        "description": "Insulated wire, cable and other insulated electric conductors",
        "chapter": "Chapter 85",
        "category": "Cables",
        "gst_rate": 18.0
    },
    
    # Chapter 90 - Optical and precision instruments
    {
        "hsn_code": "9006",
        "description": "Photographic cameras; photographic flashlight apparatus",
        "chapter": "Chapter 90",
        "category": "Photography",
        "gst_rate": 18.0
    },
    
    # Chapter 94 - Furniture
    {
        "hsn_code": "9403",
        "description": "Furniture and parts thereof",
        "chapter": "Chapter 94",
        "category": "Furniture",
        "gst_rate": 18.0
    },
    
    # Services (SAC codes)
    {
        "hsn_code": "9983",
        "description": "Repair and maintenance services of computers and peripherals",
        "chapter": "Services",
        "category": "Services",
        "gst_rate": 18.0
    },
    {
        "hsn_code": "9989",
        "description": "Other services",
        "chapter": "Services",
        "category": "Services",
        "gst_rate": 18.0
    },
]


def seed_hsn_master():
    """Seed HSN Master table with common codes."""
    for item in HSN_MASTER_DATA:
        existing = HSNMaster.query.filter_by(hsn_code=item["hsn_code"]).first()
        if not existing:
            hsn = HSNMaster(
                hsn_code=item["hsn_code"],
                description=item["description"],
                chapter=item.get("chapter"),
                category=item.get("category"),
                gst_rate=item.get("gst_rate", 18.0),
                cess_rate=item.get("cess_rate", 0.0)
            )
            db.session.add(hsn)
    
    db.session.commit()
    print(f"Seeded {len(HSN_MASTER_DATA)} HSN codes")
