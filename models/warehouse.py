from datetime import datetime
from extensions import db


class Warehouse(db.Model):
    """Godown / Warehouse / Storage Location."""
    __tablename__ = "warehouses"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    location = db.Column(db.Text)  # Address
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    stock_items = db.relationship("WarehouseStock", backref="warehouse", cascade="all, delete-orphan")


class WarehouseStock(db.Model):
    """Stock quantity per product per warehouse."""
    __tablename__ = "warehouse_stock"
    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Float, default=0.0)
    reserved_qty = db.Column(db.Float, default=0.0)  # Reserved for orders
    available_qty = db.Column(db.Float, default=0.0)  # Available = quantity - reserved
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    product = db.relationship("Product")
    
    __table_args__ = (db.UniqueConstraint('warehouse_id', 'product_id', name='uq_warehouse_product'),)


class StockMovement(db.Model):
    """Stock transaction log for audit trail."""
    __tablename__ = "stock_movements"
    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey("vouchers.id"), nullable=True)
    movement_type = db.Column(db.String(20), nullable=False)  # IN, OUT, ADJUSTMENT, TRANSFER
    quantity = db.Column(db.Float, nullable=False)
    from_warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=True)  # For transfers
    reference = db.Column(db.String(120))  # Invoice/PO number
    narration = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    warehouse = db.relationship("Warehouse", foreign_keys=[warehouse_id])
    from_warehouse = db.relationship("Warehouse", foreign_keys=[from_warehouse_id])
    product = db.relationship("Product")
    voucher = db.relationship("Voucher")
    user = db.relationship("User")


class StockBin(db.Model):
    """Bin/Rack/Shelf location within warehouse (optional granular tracking)."""
    __tablename__ = "stock_bins"
    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False, index=True)
    bin_code = db.Column(db.String(50), nullable=False)  # e.g., A-01-01 (Aisle-Rack-Shelf)
    location_description = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('warehouse_id', 'bin_code', name='uq_warehouse_bin'),)


class BinStock(db.Model):
    """Stock at bin level for precise location tracking."""
    __tablename__ = "bin_stock"
    id = db.Column(db.Integer, primary_key=True)
    bin_id = db.Column(db.Integer, db.ForeignKey("stock_bins.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Float, default=0.0)
    batch_number = db.Column(db.String(50))  # For batch tracking
    expiry_date = db.Column(db.Date, nullable=True)  # For perishables
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    bin = db.relationship("StockBin")
    product = db.relationship("Product")
    
    __table_args__ = (db.UniqueConstraint('bin_id', 'product_id', 'batch_number', name='uq_bin_product_batch'),)
