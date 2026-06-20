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
