"""GSTR JSON export for GST portal direct upload."""
import json
from datetime import datetime
from models import Voucher, VoucherItem, Party, Product


def get_gstr1_data(fy_year, month=None):
    """
    Generate GSTR-1 JSON (Outward Supplies).
    GSTR-1 is filed by suppliers for sales/outward supplies.
    """
    # Query sales vouchers for the FY
    query = Voucher.query.filter_by(voucher_type="sales", fy_year=fy_year, status="posted")
    
    if month:
        # Filter by month if provided
        query = query.filter(
            Voucher.voucher_date.between(
                f"{fy_year}-{month:02d}-01",
                f"{fy_year}-{month:02d}-31"
            )
        )
    
    vouchers = query.all()
    
    # Build GSTR-1 JSON structure
    gstr1 = {
        "gstin": "",  # Will be populated from settings
        "fp": f"{fy_year}{month:02d}" if month else f"{fy_year}01",  # Financial Period
        "gt": "OE",  # Outward supplies
        "sup": []
    }
    
    # B2B Supplies (with GSTIN)
    b2b_supplies = {}
    # B2C Supplies (without GSTIN)
    b2c_supplies = []
    
    for voucher in vouchers:
        party = voucher.party
        
        if party and party.gstin:
            # B2B Supply
            gstin = party.gstin
            if gstin not in b2b_supplies:
                b2b_supplies[gstin] = {
                    "ctin": gstin,
                    "inv": []
                }
            
            invoice_data = {
                "inum": voucher.voucher_no,
                "idt": voucher.voucher_date.strftime("%d-%m-%Y"),
                "val": round(voucher.grand_total, 2),
                "itms": []
            }
            
            for item in voucher.items:
                invoice_data["itms"].append({
                    "num": len(invoice_data["itms"]) + 1,
                    "itm_det": {
                        "hsn_sc": item.hsn_code or "0",
                        "desc": item.description or (item.product.name if item.product else ""),
                        "qty": item.qty,
                        "unit": item.unit,
                        "rt": round(item.gst_rate, 2),
                        "txval": round(item.taxable_value, 2),
                        "iamt": round(item.igst_amount, 2),
                        "camt": round(item.cgst_amount, 2),
                        "samt": round(item.sgst_amount, 2),
                        "csamt": round(item.cgst_amount + item.sgst_amount + item.igst_amount, 2)
                    }
                })
            
            b2b_supplies[gstin]["inv"].append(invoice_data)
        else:
            # B2C Supply
            b2c_item = {
                "sply_ty": "INTRA" if not voucher.is_interstate else "INTER",
                "val": round(voucher.grand_total, 2),
                "itms": []
            }
            
            for item in voucher.items:
                b2c_item["itms"].append({
                    "num": len(b2c_item["itms"]) + 1,
                    "itm_det": {
                        "hsn_sc": item.hsn_code or "0",
                        "desc": item.description or (item.product.name if item.product else ""),
                        "qty": item.qty,
                        "unit": item.unit,
                        "rt": round(item.gst_rate, 2),
                        "txval": round(item.taxable_value, 2),
                        "iamt": round(item.igst_amount, 2),
                        "camt": round(item.cgst_amount, 2),
                        "samt": round(item.sgst_amount, 2),
                        "csamt": round(item.cgst_amount + item.sgst_amount + item.igst_amount, 2)
                    }
                })
            
            b2c_supplies.append(b2c_item)
    
    # Add B2B supplies to JSON
    for gstin, supply in b2b_supplies.items():
        gstr1["sup"].append(supply)
    
    # Add B2C supplies if any
    if b2c_supplies:
        gstr1["b2c"] = b2c_supplies
    
    return gstr1


def get_gstr2_data(fy_year, month=None):
    """
    Generate GSTR-2 JSON (Inward Supplies).
    GSTR-2 is filed by recipients for purchases/inward supplies.
    """
    # Query purchase vouchers for the FY
    query = Voucher.query.filter_by(voucher_type="purchase", fy_year=fy_year, status="posted")
    
    if month:
        query = query.filter(
            Voucher.voucher_date.between(
                f"{fy_year}-{month:02d}-01",
                f"{fy_year}-{month:02d}-31"
            )
        )
    
    vouchers = query.all()
    
    gstr2 = {
        "gstin": "",  # Will be populated from settings
        "fp": f"{fy_year}{month:02d}" if month else f"{fy_year}01",
        "gt": "IE",  # Inward supplies
        "sup": []
    }
    
    # Organize by supplier GSTIN
    suppliers = {}
    
    for voucher in vouchers:
        party = voucher.party
        
        if party and party.gstin:
            gstin = party.gstin
            if gstin not in suppliers:
                suppliers[gstin] = {
                    "stin": gstin,
                    "inv": []
                }
            
            invoice_data = {
                "inum": voucher.voucher_no,
                "idt": voucher.voucher_date.strftime("%d-%m-%Y"),
                "val": round(voucher.grand_total, 2),
                "itms": []
            }
            
            for item in voucher.items:
                invoice_data["itms"].append({
                    "num": len(invoice_data["itms"]) + 1,
                    "itm_det": {
                        "hsn_sc": item.hsn_code or "0",
                        "desc": item.description or (item.product.name if item.product else ""),
                        "qty": item.qty,
                        "unit": item.unit,
                        "rt": round(item.gst_rate, 2),
                        "txval": round(item.taxable_value, 2),
                        "iamt": round(item.igst_amount, 2),
                        "camt": round(item.cgst_amount, 2),
                        "samt": round(item.sgst_amount, 2),
                        "csamt": round(item.cgst_amount + item.sgst_amount + item.igst_amount, 2)
                    }
                })
            
            suppliers[gstin]["inv"].append(invoice_data)
    
    for gstin, supplier in suppliers.items():
        gstr2["sup"].append(supplier)
    
    return gstr2


def get_gstr3b_data(fy_year, month):
    """
    Generate GSTR-3B JSON (Monthly Return).
    GSTR-3B is a simplified monthly return combining sales and purchases.
    """
    gstr3b = {
        "gstin": "",
        "fp": f"{fy_year}{month:02d}",
        "gt": "GSTR3B"
    }
    
    # Get sales data
    sales = Voucher.query.filter_by(
        voucher_type="sales", fy_year=fy_year, status="posted"
    ).filter(
        Voucher.voucher_date.between(
            f"{fy_year}-{month:02d}-01",
            f"{fy_year}-{month:02d}-31"
        )
    ).all()
    
    # Get purchase data
    purchases = Voucher.query.filter_by(
        voucher_type="purchase", fy_year=fy_year, status="posted"
    ).filter(
        Voucher.voucher_date.between(
            f"{fy_year}-{month:02d}-01",
            f"{fy_year}-{month:02d}-31"
        )
    ).all()
    
    # Calculate totals
    sales_taxable = sum(v.taxable_value for v in sales)
    sales_cgst = sum(v.cgst_amount for v in sales)
    sales_sgst = sum(v.sgst_amount for v in sales)
    sales_igst = sum(v.igst_amount for v in sales)
    
    purchase_taxable = sum(v.taxable_value for v in purchases)
    purchase_cgst = sum(v.cgst_amount for v in purchases)
    purchase_sgst = sum(v.sgst_amount for v in purchases)
    purchase_igst = sum(v.igst_amount for v in purchases)
    
    gstr3b["sup_details"] = {
        "outward": {
            "taxable_value": round(sales_taxable, 2),
            "cgst": round(sales_cgst, 2),
            "sgst": round(sales_sgst, 2),
            "igst": round(sales_igst, 2),
            "total_gst": round(sales_cgst + sales_sgst + sales_igst, 2),
            "total_value": round(sales_taxable + sales_cgst + sales_sgst + sales_igst, 2)
        },
        "inward": {
            "taxable_value": round(purchase_taxable, 2),
            "cgst": round(purchase_cgst, 2),
            "sgst": round(purchase_sgst, 2),
            "igst": round(purchase_igst, 2),
            "total_gst": round(purchase_cgst + purchase_sgst + purchase_igst, 2),
            "total_value": round(purchase_taxable + purchase_cgst + purchase_sgst + purchase_igst, 2)
        }
    }
    
    # Calculate net tax payable
    net_cgst = sales_cgst - purchase_cgst
    net_sgst = sales_sgst - purchase_sgst
    net_igst = sales_igst - purchase_igst
    
    gstr3b["tax_payable"] = {
        "cgst": round(max(0, net_cgst), 2),
        "sgst": round(max(0, net_sgst), 2),
        "igst": round(max(0, net_igst), 2),
        "total": round(max(0, net_cgst + net_sgst + net_igst), 2)
    }
    
    return gstr3b


def get_gstr9_data(fy_year):
    """
    Generate GSTR-9 JSON (Annual Return).
    GSTR-9 is the annual return consolidating all monthly data.
    """
    gstr9 = {
        "gstin": "",
        "fy": f"{fy_year}-{fy_year+1}",
        "gt": "GSTR9",
        "monthly_summary": []
    }
    
    # Aggregate data for all 12 months
    for month in range(1, 13):
        sales = Voucher.query.filter_by(
            voucher_type="sales", fy_year=fy_year, status="posted"
        ).filter(
            Voucher.voucher_date.between(
                f"{fy_year}-{month:02d}-01",
                f"{fy_year}-{month:02d}-31"
            )
        ).all()
        
        purchases = Voucher.query.filter_by(
            voucher_type="purchase", fy_year=fy_year, status="posted"
        ).filter(
            Voucher.voucher_date.between(
                f"{fy_year}-{month:02d}-01",
                f"{fy_year}-{month:02d}-31"
            )
        ).all()
        
        if sales or purchases:
            month_data = {
                "month": f"{fy_year}{month:02d}",
                "outward": {
                    "taxable_value": round(sum(v.taxable_value for v in sales), 2),
                    "cgst": round(sum(v.cgst_amount for v in sales), 2),
                    "sgst": round(sum(v.sgst_amount for v in sales), 2),
                    "igst": round(sum(v.igst_amount for v in sales), 2),
                },
                "inward": {
                    "taxable_value": round(sum(v.taxable_value for v in purchases), 2),
                    "cgst": round(sum(v.cgst_amount for v in purchases), 2),
                    "sgst": round(sum(v.sgst_amount for v in purchases), 2),
                    "igst": round(sum(v.igst_amount for v in purchases), 2),
                }
            }
            gstr9["monthly_summary"].append(month_data)
    
    # Annual totals
    all_sales = Voucher.query.filter_by(
        voucher_type="sales", fy_year=fy_year, status="posted"
    ).all()
    all_purchases = Voucher.query.filter_by(
        voucher_type="purchase", fy_year=fy_year, status="posted"
    ).all()
    
    gstr9["annual_totals"] = {
        "outward": {
            "taxable_value": round(sum(v.taxable_value for v in all_sales), 2),
            "cgst": round(sum(v.cgst_amount for v in all_sales), 2),
            "sgst": round(sum(v.sgst_amount for v in all_sales), 2),
            "igst": round(sum(v.igst_amount for v in all_sales), 2),
            "total_gst": round(sum(v.cgst_amount + v.sgst_amount + v.igst_amount for v in all_sales), 2),
        },
        "inward": {
            "taxable_value": round(sum(v.taxable_value for v in all_purchases), 2),
            "cgst": round(sum(v.cgst_amount for v in all_purchases), 2),
            "sgst": round(sum(v.sgst_amount for v in all_purchases), 2),
            "igst": round(sum(v.igst_amount for v in all_purchases), 2),
            "total_gst": round(sum(v.cgst_amount + v.sgst_amount + v.igst_amount for v in all_purchases), 2),
        }
    }
    
    return gstr9


def get_eway_bill_data(voucher_id):
    """
    Generate E-Way Bill JSON for a single sales/purchase voucher.
    E-Way Bill is required for movement of goods above ₹50,000.
    """
    voucher = Voucher.query.get(voucher_id)
    if not voucher:
        return None
    
    if voucher.grand_total < 50000:
        return {"error": "E-Way Bill not required for amounts below ₹50,000"}
    
    eway_bill = {
        "version": "1.0",
        "transaction_type": "OUT" if voucher.voucher_type == "sales" else "IN",
        "document_type": "INV",  # Invoice
        "document_number": voucher.voucher_no,
        "document_date": voucher.voucher_date.strftime("%d/%m/%Y"),
        "value_of_supply": round(voucher.grand_total, 2),
        "supply_type": "INTER" if voucher.is_interstate else "INTRA",
        "items": []
    }
    
    for item in voucher.items:
        eway_bill["items"].append({
            "item_number": len(eway_bill["items"]) + 1,
            "hsn_code": item.hsn_code or "0",
            "description": item.description or (item.product.name if item.product else ""),
            "quantity": item.qty,
            "unit": item.unit,
            "unit_price": round(item.rate, 2),
            "taxable_value": round(item.taxable_value, 2),
            "gst_rate": round(item.gst_rate, 2),
            "gst_amount": round(item.cgst_amount + item.sgst_amount + item.igst_amount, 2),
            "total": round(item.line_total, 2)
        })
    
    # Shipping details
    party = voucher.party
    eway_bill["shipping_details"] = {
        "party_name": party.name if party else "Unknown",
        "party_gstin": party.gstin if party else "",
        "party_state": party.state if party else "",
        "party_state_code": party.state_code if party else "",
        "party_address": party.address if party else ""
    }
    
    return eway_bill
