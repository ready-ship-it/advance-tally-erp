# HSN Lookup Feature - Complete Implementation Guide

## Overview

This guide covers the complete HSN (Harmonized System of Nomenclature) lookup feature implementation for the Advance Tally ERP, including auto-suggest, validation, HSN Master management, and product import from major retailers.

---

## Features Implemented

### 1. **HSN Master Database**
- Pre-seeded with 14+ common HSN codes for electronics and computers
- Supports 2, 4, 6, and 8-digit HSN codes
- Includes GST rates and CESS rates
- Categories: Computers, Electronics, Appliances, Telecom, Storage, Display, Cables, etc.

### 2. **HSN Lookup & Auto-Suggest**
- Real-time auto-suggest as users type product names
- Search by HSN code, description, or category
- Validation for HSN code format
- Popular searches tracking for analytics

### 3. **Product Import from Retailers**
- **Khosla Electronics**: khoslaonline.com
- **MDComputers**: mdcomputers.in
- **Vedanta Computers**: vedantcomputers.com
- **Flipkart**: flipkart.com
- **Amazon**: amazon.in
- **CSV Import**: Bulk upload with template

### 4. **Product Management**
- Auto-assign HSN codes to products
- Bulk HSN assignment
- Find products without HSN codes
- Suggest HSN for products based on name

---

## Database Models

### HSNMaster
```python
- hsn_code: String(20) - Unique HSN code
- description: String(500) - Product description
- chapter: String(50) - HSN chapter (e.g., "Chapter 85")
- category: String(100) - Category (e.g., "Computers")
- gst_rate: Float - GST percentage
- cess_rate: Float - CESS percentage
- is_active: Boolean - Active status
```

### HSNSearchLog
```python
- search_term: String(200) - Search query
- hsn_code_found: String(20) - HSN code found
- user_id: Integer - User who searched
- created_at: DateTime - Search timestamp
```

---

## API Endpoints

### HSN Lookup APIs

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/hsn/api/suggest?q=laptop` | GET | Get auto-suggest for search term |
| `/hsn/api/validate?code=8471` | GET | Validate HSN code format |
| `/hsn/api/search?q=computer` | GET | Search HSN by description |
| `/hsn/api/category/Computers` | GET | Get HSN codes by category |
| `/hsn/api/detail/8471` | GET | Get complete HSN details |
| `/hsn/api/bulk-assign` | POST | Bulk assign HSN to products |

### HSN Master Management

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/hsn/master` | GET | View HSN Master table |
| `/hsn/master/new` | GET/POST | Add new HSN code |
| `/hsn/master/<code>/edit` | GET/POST | Edit HSN code |
| `/hsn/export/csv` | GET | Export HSN Master to CSV |
| `/hsn/categories` | GET | View all categories |
| `/hsn/popular-searches` | GET | View popular searches |

### Product Import

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/products/import/` | GET | Import dashboard |
| `/products/import/sample` | POST | Import sample products |
| `/products/import/csv` | GET/POST | CSV import |
| `/products/import/khosla` | GET/POST | Khosla import |
| `/products/import/mdcomputers` | GET/POST | MDComputers import |
| `/products/import/vedanta` | GET/POST | Vedanta import |
| `/products/import/flipkart` | GET/POST | Flipkart import |
| `/products/import/amazon` | GET/POST | Amazon import |
| `/products/import/template/csv` | GET | Download CSV template |

---

## Common HSN Codes Reference

| HSN Code | Description | Category | GST Rate |
| :--- | :--- | :--- | :--- |
| 8471 | Computers and data processing machines | Computers | 18% |
| 8473 | Computer parts and accessories | Computer Parts | 18% |
| 8501 | Electric motors and generators | Electrical | 18% |
| 8415 | Air-conditioning machines | Appliances | 28% |
| 8517 | Telephone sets and smartphones | Telecom | 18% |
| 8523 | Storage devices (SSD, USB, etc.) | Storage | 18% |
| 8528 | Monitors and displays | Display | 18% |
| 8544 | Insulated cables and wires | Cables | 18% |

---

## CSV Import Format

### Required Columns
```
sku,name,category,hsn_code,gst_rate,unit,purchase_price,sale_price,description
```

### Example
```csv
sku,name,category,hsn_code,gst_rate,unit,purchase_price,sale_price,description
LAPTOP001,Dell Inspiron 15,Computers,8471,18,PCS,32000,45000,15-inch Full HD Display
GPU001,NVIDIA RTX 4060,Computer Parts,8473,18,PCS,18000,25000,8GB GDDR6 Memory
MONITOR001,LG 24 inch,Display,8528,18,PCS,8500,12000,Full HD 1920x1080
```

---

## Setup Instructions

### 1. Database Migration
```bash
python3 -c "from app import create_app, db; from models import HSNMaster; from services.hsn_service import seed_hsn_master; app = create_app(); db.create_all(); seed_hsn_master()"
```

### 2. Update requirements.txt
Add the following packages if not already present:
```
beautifulsoup4>=4.12.0
requests>=2.31.0
```

### 3. Deploy to Railway
1. Replace files in your repository
2. Commit and push to GitHub
3. Railway will auto-redeploy
4. Database tables will be created automatically

---

## Usage Guide

### For Admin Users

#### 1. View HSN Master
- Navigate to: **Inventory > HSN Master**
- Search by code or description
- Filter by category

#### 2. Add HSN Code
- Click "Add HSN Code"
- Enter HSN code (2, 4, 6, or 8 digits)
- Fill description, chapter, category, GST rate
- Save

#### 3. Import Products
- Navigate to: **Inventory > Import Products**
- Choose import method:
  - **Sample Products**: Load test data
  - **CSV Import**: Upload your CSV file
  - **Retailer Import**: Scrape from Khosla, MDComputers, etc.

#### 4. Assign HSN to Products
- Go to: **Inventory > Products**
- For products without HSN, use auto-suggest
- Or bulk assign via: **Inventory > Import Products > Suggest HSN**

### For Regular Users

#### 1. Auto-Suggest HSN
- When creating a product, start typing the product name
- The system will suggest matching HSN codes
- Select the correct one

#### 2. Validate HSN
- Enter HSN code in product form
- System validates format automatically
- Shows GST rate and category

---

## Troubleshooting

### Issue: "HSN code not found"
**Solution**: Check if HSN code is in the master. Add it via **Inventory > HSN Master > Add HSN Code**

### Issue: "Invalid HSN code format"
**Solution**: HSN codes must be 2, 4, 6, or 8 digits. Remove spaces and special characters.

### Issue: CSV import shows "Duplicates"
**Solution**: Products with the same SKU already exist. Update SKU in CSV or delete existing products.

### Issue: Retailer scraper returns no products
**Solution**: Website structure may have changed. Update selectors in `services/product_scraper.py`

---

## Performance Tips

1. **Caching**: HSN searches are cached for faster lookups
2. **Bulk Import**: Use CSV import for large product lists (>100 items)
3. **Search Limit**: Auto-suggest returns max 10 results to keep UI responsive
4. **Database Index**: HSN code is indexed for fast searches

---

## Official References

- **GST Portal**: https://www.gst.gov.in/
- **CBIC HSN Rates**: https://cbic-gst.gov.in/gst-goods-services-rates.html
- **ClearTax HSN Lookup**: https://cleartax.in/s/gst-hsn-lookup
- **Tally HSN Finder**: https://tallysolutions.com/business-tools-templates/free-hsn-code-finder/

---

## Support & Updates

For issues or feature requests, contact the development team or submit a GitHub issue.

Last Updated: June 2026
Version: 1.0
