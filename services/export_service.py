"""XLSX & PDF export for reports."""
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def gst_summary_to_xlsx(rows, fy):
    wb = Workbook(); ws = wb.active
    ws.title = f"GST FY {fy}"
    headers = ["Period", "Taxable Value", "CGST", "SGST", "IGST", "Total GST", "Grand Total"]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F4E78")
        c.alignment = Alignment(horizontal="center")
    for r in rows:
        ws.append([r["period"], r["taxable"], r["cgst"], r["sgst"], r["igst"], r["total_gst"], r["total"]])
    if rows:
        totals = ["TOTAL"] + [round(sum(r[k] for r in rows), 2)
                              for k in ("taxable","cgst","sgst","igst","total_gst","total")]
        ws.append(totals)
        for c in ws[ws.max_row]:
            c.font = Font(bold=True)
            c.fill = PatternFill("solid", fgColor="D9E1F2")
    for col in "BCDEFG":
        for cell in ws[col]:
            cell.number_format = "#,##0.00"
    ws.column_dimensions["A"].width = 14
    for col in "BCDEFG":
        ws.column_dimensions[col].width = 16
    buf = BytesIO(); wb.save(buf); buf.seek(0)
    return buf


def gst_summary_to_pdf(rows, fy):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), title=f"GST Monthly FY {fy}")
    styles = getSampleStyleSheet()
    elems = []
    elems.append(Paragraph(f"<b>Monthly GST Summary — FY {fy}-{str(fy+1)[2:]}</b>", styles["Title"]))
    elems.append(Spacer(1, 12))
    data = [["Period", "Taxable", "CGST", "SGST", "IGST", "Total GST", "Grand Total"]]
    for r in rows:
        data.append([
            r["period"],
            f"{r['taxable']:,.2f}", f"{r['cgst']:,.2f}", f"{r['sgst']:,.2f}",
            f"{r['igst']:,.2f}", f"{r['total_gst']:,.2f}", f"{r['total']:,.2f}",
        ])
    if rows:
        sums = {k: sum(r[k] for r in rows) for k in ("taxable","cgst","sgst","igst","total_gst","total")}
        data.append([
            "TOTAL",
            f"{sums['taxable']:,.2f}", f"{sums['cgst']:,.2f}", f"{sums['sgst']:,.2f}",
            f"{sums['igst']:,.2f}", f"{sums['total_gst']:,.2f}", f"{sums['total']:,.2f}",
        ])
    t = Table(data, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#D9E1F2")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))
    elems.append(t)
    doc.build(elems)
    buf.seek(0)
    return buf

def invoice_to_pdf(voucher, settings, amt_words):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom styles
    header_style = styles["Heading1"]
    normal_style = styles["Normal"]
    small_style = styles["Normal"].clone("Small")
    small_style.fontSize = 8
    
    elems = []
    
    # Company Letterhead
    company_name = settings.get("company_name", "Your Company Name")
    company_address = settings.get("company_address", "Address Line 1\nAddress Line 2")
    company_gstin = settings.get("company_gstin", "GSTIN: 00XXXXXXXXXXXXX")
    
    elems.append(Paragraph(f"<b>{company_name}</b>", header_style))
    elems.append(Paragraph(company_address.replace("\n", "<br/>"), normal_style))
    elems.append(Paragraph(f"GSTIN: {company_gstin}", normal_style))
    elems.append(Spacer(1, 12))
    
    elems.append(Paragraph(f"<b>TAX INVOICE</b>", styles["Heading2"]))
    elems.append(Spacer(1, 12))
    
    # Invoice Details Table
    party = voucher.party
    invoice_data = [
        [f"Invoice No: {voucher.voucher_no}", f"Date: {voucher.voucher_date}"],
        [f"Bill To: {party.name}", f"State: {party.state} ({party.state_code})"],
        [party.address.replace("\n", " "), f"GSTIN: {party.gstin}"]
    ]
    t_details = Table(invoice_data, colWidths=[250, 200])
    t_details.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elems.append(t_details)
    elems.append(Spacer(1, 12))
    
    # Items Table
    item_headers = ["SN", "Description", "HSN", "Qty", "Rate", "Taxable", "GST %", "GST Amt", "Total"]
    item_data = [item_headers]
    for i, item in enumerate(voucher.items, 1):
        gst_amt = item.cgst_amount + item.sgst_amount + item.igst_amount
        item_data.append([
            i,
            item.description or (item.product.name if item.product else ""),
            item.hsn_code or "",
            f"{item.qty} {item.unit}",
            f"{item.rate:,.2f}",
            f"{item.taxable_value:,.2f}",
            f"{item.gst_rate}%",
            f"{gst_amt:,.2f}",
            f"{item.line_total:,.2f}"
        ])
    
    # Totals
    item_data.append(["", "Total", "", "", "", f"{voucher.taxable_value:,.2f}", "", 
                      f"{(voucher.cgst_amount + voucher.sgst_amount + voucher.igst_amount):,.2f}", 
                      f"{voucher.grand_total:,.2f}"])
    
    t_items = Table(item_data, colWidths=[25, 150, 45, 40, 50, 60, 40, 50, 60])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('ALIGN', (5, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elems.append(t_items)
    elems.append(Spacer(1, 12))
    
    # Amount in words
    elems.append(Paragraph(f"<b>Amount in Words:</b> {amt_words}", normal_style))
    elems.append(Spacer(1, 24))
    
    # Footer / Signature
    footer_data = [
        ["Declaration:", f"For {company_name}"],
        ["We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.", "\n\n\nAuthorized Signatory"]
    ]
    t_footer = Table(footer_data, colWidths=[300, 150])
    t_footer.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 1), 'RIGHT'),
        ('FONTSIZE', (0, 1), (0, 1), 8),
    ]))
    elems.append(t_footer)
    
    doc.build(elems)
    buf.seek(0)
    return buf
