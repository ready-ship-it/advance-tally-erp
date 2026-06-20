from datetime import datetime
from extensions import db


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    default_hsn = db.Column(db.String(20))
    default_gst_rate = db.Column(db.Float, default=18.0)


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), unique=True, nullable=False, index=True)
    barcode = db.Column(db.String(64), unique=True, nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    hsn_code = db.Column(db.String(20))
    gst_rate = db.Column(db.Float, default=18.0)  # total GST %
    unit = db.Column(db.String(20), default="PCS")
    purchase_price = db.Column(db.Float, default=0.0)
    sale_price = db.Column(db.Float, default=0.0)
    stock_qty = db.Column(db.Float, default=0.0)
    reorder_level = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category = db.relationship("Category", backref="products")


class Party(db.Model):
    """Customer or Supplier."""
    __tablename__ = "parties"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    party_type = db.Column(db.String(20), default="customer")  # customer / supplier / both
    gstin = db.Column(db.String(20))
    state = db.Column(db.String(60), default="Maharashtra")
    state_code = db.Column(db.String(4), default="27")
    address = db.Column(db.Text)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    opening_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
