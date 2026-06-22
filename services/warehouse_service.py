"""Warehouse and stock management service."""
from datetime import datetime
from extensions import db
from models.warehouse import Warehouse, WarehouseStock, StockMovement, StockBin, BinStock
from models import Product


def create_warehouse(name, code, location):
    """Create a new warehouse."""
    warehouse = Warehouse(name=name, code=code, location=location)
    db.session.add(warehouse)
    db.session.commit()
    return warehouse


def get_warehouse_stock(warehouse_id, product_id):
    """Get stock for a product in a warehouse."""
    stock = WarehouseStock.query.filter_by(
        warehouse_id=warehouse_id,
        product_id=product_id
    ).first()
    
    if not stock:
        stock = WarehouseStock(
            warehouse_id=warehouse_id,
            product_id=product_id,
            quantity=0.0,
            available_qty=0.0
        )
        db.session.add(stock)
        db.session.commit()
    
    return stock


def update_warehouse_stock(warehouse_id, product_id, quantity, movement_type, reference="", narration="", user_id=None):
    """
    Update stock in a warehouse and create movement record.
    
    Args:
        warehouse_id: Warehouse ID
        product_id: Product ID
        quantity: Quantity to add/subtract
        movement_type: IN, OUT, ADJUSTMENT, TRANSFER
        reference: Invoice/PO number or reference
        narration: Description of movement
        user_id: User who made the movement
    """
    stock = get_warehouse_stock(warehouse_id, product_id)
    
    # Update stock quantity
    stock.quantity += quantity
    if stock.quantity < 0:
        stock.quantity = 0
    
    # Update available quantity (reserved is managed separately)
    stock.available_qty = stock.quantity - stock.reserved_qty
    stock.last_updated = datetime.utcnow()
    
    # Create movement record
    movement = StockMovement(
        warehouse_id=warehouse_id,
        product_id=product_id,
        movement_type=movement_type,
        quantity=quantity,
        reference=reference,
        narration=narration,
        created_by=user_id
    )
    
    db.session.add(movement)
    db.session.commit()
    
    return stock


def transfer_stock(from_warehouse_id, to_warehouse_id, product_id, quantity, reference="", narration="", user_id=None):
    """Transfer stock from one warehouse to another."""
    # Deduct from source warehouse
    from_stock = get_warehouse_stock(from_warehouse_id, product_id)
    if from_stock.available_qty < quantity:
        return False, "Insufficient stock in source warehouse"
    
    # Create OUT movement in source warehouse
    movement_out = StockMovement(
        warehouse_id=from_warehouse_id,
        product_id=product_id,
        movement_type="TRANSFER",
        quantity=-quantity,
        reference=reference,
        narration=f"Transfer to warehouse {to_warehouse_id}: {narration}",
        created_by=user_id
    )
    
    # Create IN movement in destination warehouse
    movement_in = StockMovement(
        warehouse_id=to_warehouse_id,
        product_id=product_id,
        movement_type="TRANSFER",
        quantity=quantity,
        from_warehouse_id=from_warehouse_id,
        reference=reference,
        narration=f"Transfer from warehouse {from_warehouse_id}: {narration}",
        created_by=user_id
    )
    
    # Update stock quantities
    from_stock.quantity -= quantity
    from_stock.available_qty = from_stock.quantity - from_stock.reserved_qty
    from_stock.last_updated = datetime.utcnow()
    
    to_stock = get_warehouse_stock(to_warehouse_id, product_id)
    to_stock.quantity += quantity
    to_stock.available_qty = to_stock.quantity - to_stock.reserved_qty
    to_stock.last_updated = datetime.utcnow()
    
    db.session.add(movement_out)
    db.session.add(movement_in)
    db.session.commit()
    
    return True, "Stock transferred successfully"


def get_warehouse_summary(warehouse_id):
    """Get stock summary for a warehouse."""
    stocks = WarehouseStock.query.filter_by(warehouse_id=warehouse_id).all()
    
    summary = {
        "warehouse_id": warehouse_id,
        "total_items": len(stocks),
        "total_quantity": sum(s.quantity for s in stocks),
        "total_available": sum(s.available_qty for s in stocks),
        "total_reserved": sum(s.reserved_qty for s in stocks),
        "items": []
    }
    
    for stock in stocks:
        summary["items"].append({
            "product_id": stock.product_id,
            "product_name": stock.product.name if stock.product else "Unknown",
            "quantity": stock.quantity,
            "available": stock.available_qty,
            "reserved": stock.reserved_qty,
            "sku": stock.product.sku if stock.product else "",
            "unit": stock.product.unit if stock.product else "PCS"
        })
    
    return summary


def get_stock_movement_history(warehouse_id=None, product_id=None, days=30):
    """Get stock movement history."""
    query = StockMovement.query
    
    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)
    
    if product_id:
        query = query.filter_by(product_id=product_id)
    
    movements = query.order_by(StockMovement.created_at.desc()).limit(100).all()
    
    return [{
        "id": m.id,
        "warehouse": m.warehouse.name if m.warehouse else "",
        "product": m.product.name if m.product else "",
        "type": m.movement_type,
        "quantity": m.quantity,
        "reference": m.reference,
        "narration": m.narration,
        "created_by": m.user.username if m.user else "",
        "created_at": m.created_at.isoformat()
    } for m in movements]


def create_bin(warehouse_id, bin_code, location_description):
    """Create a bin/rack/shelf in a warehouse."""
    bin = StockBin(
        warehouse_id=warehouse_id,
        bin_code=bin_code,
        location_description=location_description
    )
    db.session.add(bin)
    db.session.commit()
    return bin


def update_bin_stock(bin_id, product_id, quantity, batch_number=None, expiry_date=None):
    """Update stock at bin level."""
    bin_stock = BinStock.query.filter_by(
        bin_id=bin_id,
        product_id=product_id,
        batch_number=batch_number
    ).first()
    
    if not bin_stock:
        bin_stock = BinStock(
            bin_id=bin_id,
            product_id=product_id,
            batch_number=batch_number,
            expiry_date=expiry_date,
            quantity=0.0
        )
        db.session.add(bin_stock)
    
    bin_stock.quantity += quantity
    if bin_stock.quantity < 0:
        bin_stock.quantity = 0
    
    bin_stock.last_updated = datetime.utcnow()
    db.session.commit()
    
    return bin_stock


def get_bin_contents(bin_id):
    """Get all items in a bin."""
    items = BinStock.query.filter_by(bin_id=bin_id).all()
    
    return [{
        "product_id": item.product_id,
        "product_name": item.product.name if item.product else "",
        "quantity": item.quantity,
        "batch_number": item.batch_number,
        "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
        "sku": item.product.sku if item.product else ""
    } for item in items]


def get_low_stock_items(warehouse_id=None):
    """Get items below reorder level."""
    query = WarehouseStock.query.join(Product)
    
    if warehouse_id:
        query = query.filter(WarehouseStock.warehouse_id == warehouse_id)
    
    low_stock = query.filter(WarehouseStock.quantity <= Product.reorder_level).all()
    
    return [{
        "warehouse_id": stock.warehouse_id,
        "warehouse_name": stock.warehouse.name if stock.warehouse else "",
        "product_id": stock.product_id,
        "product_name": stock.product.name if stock.product else "",
        "sku": stock.product.sku if stock.product else "",
        "current_qty": stock.quantity,
        "reorder_level": stock.product.reorder_level if stock.product else 0,
        "unit": stock.product.unit if stock.product else "PCS"
    } for stock in low_stock]
