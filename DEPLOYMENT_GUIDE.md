# Deployment and Testing Guide

## Pre-Deployment Checklist

### 1. Code Review
- [x] All new files created
- [x] All routes registered in app.py
- [x] All models imported in models/__init__.py
- [x] No syntax errors
- [x] Code follows project conventions

### 2. Database Setup
```bash
# Create new tables
python3 << 'PYTHON'
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print("Database tables created successfully")
PYTHON
```

### 3. Dependencies
```bash
# All required packages are in requirements.txt
pip install -r requirements.txt

# Verify installations
python3 -c "import reportlab; import xml.etree.ElementTree; print('All dependencies OK')"
```

### 4. Configuration

**Email Settings** (`/admin/settings`):
```
email_smtp_server: smtp.gmail.com
email_smtp_port: 587
email_sender: your-email@gmail.com
email_password: your-app-password
email_use_tls: true
```

**Company Settings** (`/admin/settings`):
```
company_name: Your Company Name
company_address: Address Line 1, Address Line 2
company_gstin: 27AABCT1234H1Z0
company_state: Maharashtra
company_state_code: 27
```

---

## Testing Guide

### 1. Invoice PDF Testing

**Test Case 1**: Generate PDF for existing invoice
```bash
curl http://localhost:5000/vouchers/pdf/1 -o invoice.pdf
# Verify PDF opens and contains company letterhead
```

**Test Case 2**: Verify amount in words
- Create invoice with amount 1,234.50
- Download PDF
- Verify: "One Thousand Two Hundred Thirty Four Rupees and Fifty Paise Only"

**Test Case 3**: Multiple items with GST
- Create invoice with 3 items
- Verify all items appear in PDF
- Verify GST breakdown (CGST, SGST, IGST)

---

### 2. GSTR Export Testing

**Test Case 1**: GSTR-1 Export
```bash
curl http://localhost:5000/reports/gstr1/export?month=1 -o gstr1.json
# Verify JSON structure
# Check B2B and B2C segregation
```

**Test Case 2**: GSTR-3B Export
```bash
curl http://localhost:5000/reports/gstr3b/export?month=1 -o gstr3b.json
# Verify outward and inward totals
# Check net tax payable calculation
```

**Test Case 3**: E-Way Bill Export
```bash
curl http://localhost:5000/reports/eway-bill/1/export -o eway.json
# Verify amount >= 50000
# Check party details
```

---

### 3. Warehouse Testing

**Test Case 1**: Create Warehouse
```
POST /warehouse/new
- Name: Main Warehouse
- Code: WH001
- Location: Mumbai
```

**Test Case 2**: Add Stock
```
POST /warehouse/1/stock/add
- Product: 1
- Quantity: 100
- Reference: PO-001
```

**Test Case 3**: Transfer Stock
```
POST /warehouse/transfer
- From: 1
- To: 2
- Product: 1
- Quantity: 50
```

**Test Case 4**: Low Stock Alert
```
GET /warehouse/low-stock
# Verify items below reorder level are listed
```

---

### 4. Bank Reconciliation Testing

**Test Case 1**: Create Bank Account
```
POST /bank/accounts/new
- Account Name: HDFC Savings
- Account Number: 123456789
- IFSC: HDFC0000001
- Bank: HDFC Bank
```

**Test Case 2**: Import Statements
```
POST /bank/accounts/1/import
- Upload CSV with transactions
- Verify import count
```

**Test Case 3**: Reconcile Statements
```
POST /bank/reconciliation/1/match
- Match statement with ledger entry
- Verify amounts match
```

**Test Case 4**: Generate Report
```
GET /bank/reconciliation/1/report
# Verify bank balance vs book balance
# Check adjustments for cheques and deposits
```

---

### 5. Tally Import/Export Testing

**Test Case 1**: Export to XML
```
GET /tally/export/xml
# Verify XML structure
# Check all master data included
```

**Test Case 2**: Export to CSV
```
GET /tally/export/csv/products
# Verify CSV format
# Check all products included
```

**Test Case 3**: Import from CSV
```
POST /tally/import/csv/products
- Upload products.csv
- Verify import count
- Check for duplicates
```

---

### 6. Email Testing

**Test Case 1**: Test Email Configuration
```
POST /email/test
- Recipient: your-email@example.com
- Verify test email received
```

**Test Case 2**: Send Invoice Email
```
POST /email/invoice/1
- Recipient: customer@example.com
- Verify PDF attachment
- Check amount in words
```

**Test Case 3**: Bulk Send
```
POST /email/bulk-send
- Select 5 invoices
- Send to all parties
- Verify success count
```

**Test Case 4**: Payment Reminder
```
POST /email/reminder/1/overdue
- Verify reminder email sent
- Check content
```

---

## Integration Testing

### End-to-End Workflow

**Scenario**: Complete invoice to payment workflow

1. **Create Invoice**
   - Create sales voucher with items
   - Verify GST calculation

2. **Generate PDF**
   - Download invoice PDF
   - Verify letterhead and amount-in-words

3. **Send Email**
   - Send invoice to customer
   - Verify PDF attachment

4. **Export GSTR**
   - Export GSTR-1 JSON
   - Verify invoice included

5. **Bank Reconciliation**
   - Record payment in bank
   - Import bank statement
   - Match with ledger entry

---

## Performance Testing

### Load Testing

**Test**: Generate 100 invoices and export GSTR
```bash
# Time should be < 5 seconds
time curl http://localhost:5000/reports/gstr1/export > /dev/null
```

**Test**: Warehouse stock query with 1000 items
```bash
# Should return in < 1 second
time curl http://localhost:5000/warehouse/api/warehouse/1/summary > /dev/null
```

---

## Security Testing

### Test Cases

1. **Authentication**
   - Verify unauthenticated access denied
   - Verify admin-only routes protected

2. **Authorization**
   - User cannot access other user's data
   - Admin can access all data

3. **Input Validation**
   - Test SQL injection attempts
   - Test XSS attempts
   - Test file upload restrictions

4. **Data Protection**
   - Email credentials not exposed
   - Bank data encrypted
   - Audit trail maintained

---

## Error Handling Testing

### Test Cases

1. **Invalid Email**
   - Test with invalid SMTP settings
   - Verify error message

2. **Missing Data**
   - Test with incomplete invoice
   - Verify error handling

3. **Duplicate Import**
   - Test importing same data twice
   - Verify duplicate prevention

4. **File Upload**
   - Test with invalid file format
   - Test with corrupted file

---

## Deployment Steps

### 1. Prepare Environment
```bash
# Clone repository
git clone https://github.com/ready-ship-it/advance-tally-erp.git
cd advance-tally-erp

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Migration
```bash
# Create tables
python3 << 'PYTHON'
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
PYTHON
```

### 3. Configure Settings
```bash
# Set environment variables
export FLASK_ENV=production
export SECRET_KEY=your-secret-key
export DATABASE_URL=mysql://user:pass@localhost/dbname
```

### 4. Initialize Data
```bash
# Run seed script if needed
python3 scripts/init_db.py
```

### 5. Start Application
```bash
# Development
python3 app.py

# Production
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 6. Verify Deployment
```bash
# Test health check
curl http://localhost:5000/

# Test key endpoints
curl http://localhost:5000/dashboard
curl http://localhost:5000/warehouse
curl http://localhost:5000/bank/accounts
```

---

## Troubleshooting

### Common Issues

**Issue**: Database tables not created
```
Solution: Run db.create_all() in app context
```

**Issue**: Email not sending
```
Solution: 
1. Check SMTP settings in admin panel
2. Verify sender email and password
3. Test with /email/test endpoint
4. Check firewall/network settings
```

**Issue**: PDF generation fails
```
Solution:
1. Verify reportlab is installed
2. Check company settings are configured
3. Verify party information is complete
```

**Issue**: Warehouse stock not updating
```
Solution:
1. Verify warehouse exists
2. Check product exists
3. Verify user has permission
4. Check database for errors
```

---

## Rollback Procedure

If deployment fails:

```bash
# 1. Stop application
kill $(lsof -t -i:5000)

# 2. Revert code
git revert HEAD

# 3. Restart with previous version
python3 app.py
```

---

## Monitoring

### Key Metrics to Monitor

1. **Application Health**
   - Response time
   - Error rate
   - Database connections

2. **Email Delivery**
   - Send success rate
   - Delivery time
   - Bounce rate

3. **Warehouse Operations**
   - Stock accuracy
   - Transaction volume
   - Query performance

4. **Bank Reconciliation**
   - Reconciliation success rate
   - Variance amount
   - Processing time

---

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**
   - Check error logs
   - Verify email delivery
   - Monitor database size

2. **Monthly**
   - Archive old stock movements
   - Review bank reconciliations
   - Update security patches

3. **Quarterly**
   - Performance optimization
   - Database cleanup
   - Security audit

---

**Last Updated**: January 2025
**Status**: Production Ready
