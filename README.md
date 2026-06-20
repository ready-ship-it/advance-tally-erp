# Tally-style ERP (Flask + MySQL)

A small Tally-inspired ERP with Indian GST (CGST / SGST / IGST), HSN auto-fill,
barcode scanner support, role-based access, automated server backups with
retention + FTP upload, FY year selector, and XLS/PDF GST reports.

Designed to be pushed to **GitHub** and deployed to **Railway** with a
managed MySQL plugin.

## Features

| Area | Detail |
|---|---|
| Roles | `master_admin` · `admin` · `user` (Tally-like permission tiers) |
| FY selector | After login, choose any year from current year → 2030 |
| Inventory | Products with SKU, **barcode**, HSN, GST%, unit, stock, reorder |
| HSN auto | Pre-loaded HSN library (computer parts + appliances). Auto from category, suggest from name. |
| Categories | 15 pre-seeded categories with default HSN + GST |
| Seed data | 50 computer parts + 50 home appliances with realistic HSN & GST |
| Vouchers | Sales / Purchase invoice (multi-line GST) + Receipt / Payment |
| GST | CGST + SGST for intra-state, IGST for inter-state (state-code aware) |
| GST rate | Editable per product and per voucher line |
| Reports | Day Book · Ledger statement · Profit & Loss · **Monthly GST summary** |
| Export | GST monthly export to **XLSX** and **PDF** |
| Backup | Auto every **2 hours** + manual button · keeps last **5** |
| Restore | One-click restore from any kept backup (master-admin only) |
| FTP | One-click upload of any backup to a configured FTP / FTPS server |

## Default logins (change after first login)

| Username | Password | Role |
|---|---|---|
| `master` | `master@123` | master_admin |
| `admin` | `admin@123` | admin |
| `user` | `user@123` | user |

## Deploy on Railway

1. Create a GitHub repo, push this folder.
2. In Railway: **New Project → Deploy from GitHub repo**.
3. **+ Add Service → Database → MySQL.** Railway auto-injects `MYSQL_URL`.
4. Open your service → **Variables**, add:
   - `SECRET_KEY` (long random string)
   - `FTP_HOST`, `FTP_USER`, `FTP_PASSWORD`, `FTP_REMOTE_DIR` *(optional)*
   - `BACKUP_INTERVAL_HOURS=2` (already default)
   - `BACKUP_KEEP_LAST=5` (already default)
5. Deploy. First boot creates tables and seeds the catalog.

The app exposes port `$PORT` (Railway-provided) via gunicorn.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # edit DB_* and SECRET_KEY
python scripts/init_db.py  # creates schema + seeds master/admin/user + 100 products
flask --app app run --debug
```

Open <http://localhost:5000>, log in as `master / master@123`, pick a financial year and start working.

## File layout

```
app.py               Flask factory + scheduler bootstrap
config.py            Env-driven config (DB, FTP, backup cadence)
extensions.py        db (SQLAlchemy)
utils.py             Decorators: login_required_full, admin_required, master_required
models/              User, Product, Voucher, Ledger, BackupLog, Setting, Party, Category
routes/
  auth.py            login / logout / select-year
  dashboard.py       FY-scoped KPIs
  inventory.py       Products, categories, parties, barcode lookup, HSN suggest
  vouchers.py        Sales/Purchase invoices, Receipt/Payment, ledger postings
  reports.py         Day Book, Ledger statement, P&L, GST monthly + XLS/PDF export
  backup.py          Backup list, run, restore, FTP upload, delete
  admin.py           Users & roles, company settings
services/
  hsn_service.py     Local HSN library lookup
  backup_service.py  mysqldump (preferred) / logical JSON dump, retention, scheduler
  ftp_service.py     FTP / FTPS uploader
  export_service.py  openpyxl + reportlab exporters
data/
  hsn_codes.json     Pre-loaded HSN codes (CBIC-style)
  seed_products.py   100 sample products + chart of accounts + demo users
templates/, static/  UI
scripts/init_db.py   One-shot DB setup for local dev
Procfile, railway.json, nixpacks.toml   Railway/Heroku deploy
```

## How GST is computed

- Each product has a `gst_rate` (default 18%).
  Categories store a `default_gst_rate` used when a new product is created.
- Sales/Purchase invoice line: `taxable = qty × rate × (1 − disc%/100)`.
- **Intra-state** (party state code = company state code) → split into
  `CGST = SGST = taxable × (gst/2)/100`.
- **Inter-state** (party state code differs) → `IGST = taxable × gst/100`.
  The UI auto-flips the IGST toggle when the selected party's state code
  isn't `27` (Maharashtra, the seeded default — change in Company Settings).
- Grand total is rounded to nearest rupee; `round_off` captures the difference.

## Backup model

- **Scheduler:** APScheduler runs `run_backup(mode="auto")` every
  `BACKUP_INTERVAL_HOURS` (default 2).
- **Manual:** any admin can click *Run Backup Now* (e.g. every hour).
- Both feed the same rolling window of `BACKUP_KEEP_LAST` (default 5).
- Backups try `mysqldump`; on Railway's MySQL plugin the dump streams to
  `backups/tally_backup_YYYYMMDD-HHMMSS_<mode>.sql.gz`. If `mysqldump`
  isn't installed, the service falls back to a `*.json.gz` logical dump.
- **Restore** (master-admin only) wipes & repopulates from a chosen file.
- **FTP**: any admin can upload a chosen backup file to the configured FTP
  server. Set `FTP_USE_TLS=true` to use FTPS.

## HSN auto-fill

- Built-in dictionary `data/hsn_codes.json` covers common computer parts
  and home appliances aligned with CBIC HSN/SAC categories.
- On the product form: select a category to auto-fill its default HSN +
  GST, OR click **"Suggest from name"** to query the dictionary by keyword.
- The "Free HSN Code Finder" page at
  <https://tallysolutions.com/business-tools-templates/free-hsn-code-finder>
  has no public API; this app ships the same data locally so lookups are
  fast, deterministic, and don't depend on a third-party site.

## Roles & permissions

| Action | master | admin | user |
|---|:-:|:-:|:-:|
| Login + view all | ✓ | ✓ | ✓ |
| Create vouchers | ✓ | ✓ | ✓ |
| Add/edit products, parties | ✓ | ✓ | — |
| Run backup, FTP upload | ✓ | ✓ | — |
| Download / **restore** backup | ✓ | — | — |
| Manage users & roles | ✓ | — | — |
| Edit company settings | ✓ | ✓ | — |

## Notes & limitations

- Hosting on Railway means backups land on Railway's ephemeral filesystem
  *for this service*. Push them off-box via FTP for true persistence, or
  attach a Railway Volume mount at `/app/backups` for durable storage.
- This is a starter ERP, not a Tally replacement: no GSTR-1/3B filing
  export, no bank reconciliation, no e-way bill, no batch/serial inventory.
  All of those can be layered on top of the existing model.
