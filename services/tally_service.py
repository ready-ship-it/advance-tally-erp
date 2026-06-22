"""Tally XML import/export service for data migration."""
import xml.etree.ElementTree as ET
from datetime import datetime, date
from extensions import db
from models import (
    Category, Product, Party, Ledger, Voucher, VoucherItem,
    LedgerEntry, User
)


def export_to_tally_xml(company_name="Company", fy_year=2025):
    """
    Export data to Tally-compatible XML format.
    """
    root = ET.Element("ENVELOPE")
    root.set("xmlns:UDF", "TallyUDF")
    
    # Company header
    header = ET.SubElement(root, "HEADER")
    ET.SubElement(header, "TALLYREQUEST").text = "Export"
    ET.SubElement(header, "TALLYVERSION").text = "9.2.0"
    ET.SubElement(header, "REQUESTDESC").text = "ERP Export to Tally"
    
    # Company
    company = ET.SubElement(root, "COMPANY")
    ET.SubElement(company, "NAME").text = company_name
    ET.SubElement(company, "MADDRESS").text = "Address"
    ET.SubElement(company, "MPHONE").text = "Phone"
    ET.SubElement(company, "MEMAIL").text = "Email"
    
    # Financial Year
    fy = ET.SubElement(company, "FINANCIALYEAR")
    ET.SubElement(fy, "STARTINGDATE").text = f"{fy_year}-04-01"
    ET.SubElement(fy, "ENDINGDATE").text = f"{fy_year+1}-03-31"
    
    # Export categories
    categories = Category.query.all()
    for cat in categories:
        cat_elem = ET.SubElement(company, "CATEGORY")
        ET.SubElement(cat_elem, "NAME").text = cat.name
        ET.SubElement(cat_elem, "PARENT").text = "Primary"
        ET.SubElement(cat_elem, "GSTRATE").text = str(cat.default_gst_rate)
    
    # Export products
    for product in Product.query.all():
        prod_elem = ET.SubElement(company, "ITEM")
        ET.SubElement(prod_elem, "NAME").text = product.name
        ET.SubElement(prod_elem, "CATEGORY").text = product.category.name if product.category else "Primary"
        ET.SubElement(prod_elem, "DESCRIPTION").text = product.description or ""
        ET.SubElement(prod_elem, "HSN").text = product.hsn_code or ""
        ET.SubElement(prod_elem, "GSTRATE").text = str(product.gst_rate)
        ET.SubElement(prod_elem, "UNIT").text = product.unit
        ET.SubElement(prod_elem, "OPENINGBALANCE").text = str(product.stock_qty)
        ET.SubElement(prod_elem, "RATE").text = str(product.sale_price)
    
    # Export parties
    for party in Party.query.all():
        party_elem = ET.SubElement(company, "PARTY")
        ET.SubElement(party_elem, "NAME").text = party.name
        ET.SubElement(party_elem, "TYPE").text = party.party_type.upper()
        ET.SubElement(party_elem, "GSTIN").text = party.gstin or ""
        ET.SubElement(party_elem, "STATE").text = party.state
        ET.SubElement(party_elem, "STATECODE").text = party.state_code
        ET.SubElement(party_elem, "ADDRESS").text = party.address or ""
        ET.SubElement(party_elem, "PHONE").text = party.phone or ""
        ET.SubElement(party_elem, "EMAIL").text = party.email or ""
        ET.SubElement(party_elem, "OPENINGBALANCE").text = str(party.opening_balance)
    
    # Export ledgers
    for ledger in Ledger.query.all():
        ledger_elem = ET.SubElement(company, "LEDGER")
        ET.SubElement(ledger_elem, "NAME").text = ledger.name
        ET.SubElement(ledger_elem, "GROUP").text = ledger.group_name
        ET.SubElement(ledger_elem, "OPENINGBALANCE").text = str(ledger.opening_balance or 0)
    
    # Export vouchers
    for voucher in Voucher.query.filter_by(status="posted").all():
        voucher_elem = ET.SubElement(company, "VOUCHER")
        ET.SubElement(voucher_elem, "VOUCHERNUMBER").text = voucher.voucher_no
        ET.SubElement(voucher_elem, "VOUCHERTYPE").text = voucher.voucher_type.upper()
        ET.SubElement(voucher_elem, "DATE").text = voucher.voucher_date.strftime("%d-%m-%Y")
        ET.SubElement(voucher_elem, "REFERENCE").text = voucher.reference or ""
        ET.SubElement(voucher_elem, "NARRATION").text = voucher.narration or ""
        
        if voucher.party:
            ET.SubElement(voucher_elem, "PARTY").text = voucher.party.name
        
        # Voucher items
        for item in voucher.items:
            item_elem = ET.SubElement(voucher_elem, "ITEM")
            ET.SubElement(item_elem, "DESCRIPTION").text = item.description or (item.product.name if item.product else "")
            ET.SubElement(item_elem, "HSN").text = item.hsn_code or ""
            ET.SubElement(item_elem, "QUANTITY").text = str(item.qty)
            ET.SubElement(item_elem, "UNIT").text = item.unit
            ET.SubElement(item_elem, "RATE").text = str(item.rate)
            ET.SubElement(item_elem, "AMOUNT").text = str(item.line_total)
            ET.SubElement(item_elem, "GSTRATE").text = str(item.gst_rate)
            ET.SubElement(item_elem, "CGST").text = str(item.cgst_amount)
            ET.SubElement(item_elem, "SGST").text = str(item.sgst_amount)
            ET.SubElement(item_elem, "IGST").text = str(item.igst_amount)
        
        # Voucher totals
        ET.SubElement(voucher_elem, "SUBTOTAL").text = str(voucher.sub_total)
        ET.SubElement(voucher_elem, "DISCOUNT").text = str(voucher.discount)
        ET.SubElement(voucher_elem, "TAXABLEVALUE").text = str(voucher.taxable_value)
        ET.SubElement(voucher_elem, "CGST").text = str(voucher.cgst_amount)
        ET.SubElement(voucher_elem, "SGST").text = str(voucher.sgst_amount)
        ET.SubElement(voucher_elem, "IGST").text = str(voucher.igst_amount)
        ET.SubElement(voucher_elem, "ROUNDOFF").text = str(voucher.round_off)
        ET.SubElement(voucher_elem, "GRANDTOTAL").text = str(voucher.grand_total)
    
    # Convert to string
    tree = ET.ElementTree(root)
    xml_str = ET.tostring(root, encoding='unicode')
    
    # Pretty print
    from xml.dom import minidom
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent="  ")


def import_from_tally_xml(xml_file_path, user_id=1):
    """
    Import data from Tally XML export.
    """
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    imported = {
        "categories": 0,
        "products": 0,
        "parties": 0,
        "ledgers": 0,
        "vouchers": 0
    }
    
    # Import categories
    for cat_elem in root.findall("CATEGORY"):
        name = cat_elem.findtext("NAME", "")
        if not name:
            continue
        
        existing = Category.query.filter_by(name=name).first()
        if not existing:
            cat = Category(
                name=name,
                default_gst_rate=float(cat_elem.findtext("GSTRATE", 18.0) or 18.0)
            )
            db.session.add(cat)
            imported["categories"] += 1
    
    db.session.commit()
    
    # Import products
    for prod_elem in root.findall("ITEM"):
        name = prod_elem.findtext("NAME", "")
        if not name:
            continue
        
        existing = Product.query.filter_by(name=name).first()
        if not existing:
            category_name = prod_elem.findtext("CATEGORY", "Primary")
            category = Category.query.filter_by(name=category_name).first()
            
            product = Product(
                sku=prod_elem.findtext("SKU", name[:10]),
                name=name,
                description=prod_elem.findtext("DESCRIPTION", ""),
                category_id=category.id if category else None,
                hsn_code=prod_elem.findtext("HSN", ""),
                gst_rate=float(prod_elem.findtext("GSTRATE", 18.0) or 18.0),
                unit=prod_elem.findtext("UNIT", "PCS"),
                stock_qty=float(prod_elem.findtext("OPENINGBALANCE", 0) or 0),
                sale_price=float(prod_elem.findtext("RATE", 0) or 0)
            )
            db.session.add(product)
            imported["products"] += 1
    
    db.session.commit()
    
    # Import parties
    for party_elem in root.findall("PARTY"):
        name = party_elem.findtext("NAME", "")
        if not name:
            continue
        
        existing = Party.query.filter_by(name=name).first()
        if not existing:
            party = Party(
                name=name,
                party_type=party_elem.findtext("TYPE", "customer").lower(),
                gstin=party_elem.findtext("GSTIN", ""),
                state=party_elem.findtext("STATE", "Maharashtra"),
                state_code=party_elem.findtext("STATECODE", "27"),
                address=party_elem.findtext("ADDRESS", ""),
                phone=party_elem.findtext("PHONE", ""),
                email=party_elem.findtext("EMAIL", ""),
                opening_balance=float(party_elem.findtext("OPENINGBALANCE", 0) or 0)
            )
            db.session.add(party)
            imported["parties"] += 1
    
    db.session.commit()
    
    # Import ledgers
    for ledger_elem in root.findall("LEDGER"):
        name = ledger_elem.findtext("NAME", "")
        if not name:
            continue
        
        existing = Ledger.query.filter_by(name=name).first()
        if not existing:
            ledger = Ledger(
                name=name,
                group_name=ledger_elem.findtext("GROUP", "Sundry Debtors"),
                opening_balance=float(ledger_elem.findtext("OPENINGBALANCE", 0) or 0)
            )
            db.session.add(ledger)
            imported["ledgers"] += 1
    
    db.session.commit()
    
    return imported


def export_to_csv(export_type="products"):
    """Export data to CSV format."""
    import csv
    from io import StringIO
    
    output = StringIO()
    
    if export_type == "products":
        writer = csv.DictWriter(output, fieldnames=[
            "SKU", "Name", "Category", "HSN Code", "GST Rate", "Unit",
            "Purchase Price", "Sale Price", "Stock Qty", "Reorder Level"
        ])
        writer.writeheader()
        
        for product in Product.query.all():
            writer.writerow({
                "SKU": product.sku,
                "Name": product.name,
                "Category": product.category.name if product.category else "",
                "HSN Code": product.hsn_code or "",
                "GST Rate": product.gst_rate,
                "Unit": product.unit,
                "Purchase Price": product.purchase_price,
                "Sale Price": product.sale_price,
                "Stock Qty": product.stock_qty,
                "Reorder Level": product.reorder_level
            })
    
    elif export_type == "parties":
        writer = csv.DictWriter(output, fieldnames=[
            "Name", "Type", "GSTIN", "State", "State Code",
            "Address", "Phone", "Email", "Opening Balance"
        ])
        writer.writeheader()
        
        for party in Party.query.all():
            writer.writerow({
                "Name": party.name,
                "Type": party.party_type,
                "GSTIN": party.gstin or "",
                "State": party.state,
                "State Code": party.state_code,
                "Address": party.address or "",
                "Phone": party.phone or "",
                "Email": party.email or "",
                "Opening Balance": party.opening_balance
            })
    
    elif export_type == "vouchers":
        writer = csv.DictWriter(output, fieldnames=[
            "Voucher No", "Type", "Date", "Party", "Reference",
            "Taxable Value", "CGST", "SGST", "IGST", "Grand Total"
        ])
        writer.writeheader()
        
        for voucher in Voucher.query.filter_by(status="posted").all():
            writer.writerow({
                "Voucher No": voucher.voucher_no,
                "Type": voucher.voucher_type,
                "Date": voucher.voucher_date.strftime("%d-%m-%Y"),
                "Party": voucher.party.name if voucher.party else "",
                "Reference": voucher.reference or "",
                "Taxable Value": voucher.taxable_value,
                "CGST": voucher.cgst_amount,
                "SGST": voucher.sgst_amount,
                "IGST": voucher.igst_amount,
                "Grand Total": voucher.grand_total
            })
    
    output.seek(0)
    return output.getvalue()


def import_from_csv(csv_file_path, import_type="products"):
    """Import data from CSV file."""
    import csv
    
    imported = 0
    errors = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            if import_type == "products":
                for row in reader:
                    try:
                        sku = row.get("SKU", "").strip()
                        if not sku or Product.query.filter_by(sku=sku).first():
                            continue
                        
                        category_name = row.get("Category", "").strip()
                        category = Category.query.filter_by(name=category_name).first() if category_name else None
                        
                        product = Product(
                            sku=sku,
                            name=row.get("Name", "").strip(),
                            category_id=category.id if category else None,
                            hsn_code=row.get("HSN Code", "").strip(),
                            gst_rate=float(row.get("GST Rate", 18.0) or 18.0),
                            unit=row.get("Unit", "PCS").strip(),
                            purchase_price=float(row.get("Purchase Price", 0) or 0),
                            sale_price=float(row.get("Sale Price", 0) or 0),
                            stock_qty=float(row.get("Stock Qty", 0) or 0),
                            reorder_level=float(row.get("Reorder Level", 0) or 0)
                        )
                        db.session.add(product)
                        imported += 1
                    except Exception as e:
                        errors.append(f"Row {imported+1}: {str(e)}")
            
            elif import_type == "parties":
                for row in reader:
                    try:
                        name = row.get("Name", "").strip()
                        if not name or Party.query.filter_by(name=name).first():
                            continue
                        
                        party = Party(
                            name=name,
                            party_type=row.get("Type", "customer").lower(),
                            gstin=row.get("GSTIN", "").strip(),
                            state=row.get("State", "Maharashtra").strip(),
                            state_code=row.get("State Code", "27").strip(),
                            address=row.get("Address", "").strip(),
                            phone=row.get("Phone", "").strip(),
                            email=row.get("Email", "").strip(),
                            opening_balance=float(row.get("Opening Balance", 0) or 0)
                        )
                        db.session.add(party)
                        imported += 1
                    except Exception as e:
                        errors.append(f"Row {imported+1}: {str(e)}")
        
        db.session.commit()
        return imported, errors
    
    except Exception as e:
        return 0, [str(e)]
