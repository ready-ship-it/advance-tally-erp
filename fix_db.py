"""
Diagnostic and migration script to fix database errors on Railway.
Run this via the Railway console or by deploying it once.
"""
from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

def run_migration():
    with app.app_context():
        print("Starting database diagnostic and migration...")
        
        # 1. Add transaction_id to vouchers table
        try:
            db.session.execute(text("ALTER TABLE vouchers ADD COLUMN transaction_id VARCHAR(100)"))
            db.session.commit()
            print("Successfully added 'transaction_id' column to 'vouchers' table.")
        except Exception as e:
            if "Duplicate column name" in str(e) or "already exists" in str(e).lower():
                print("'transaction_id' column already exists in 'vouchers' table. Skipping.")
            else:
                print(f"Error adding 'transaction_id' column: {e}")
        
        # 2. Ensure all tables are created (idempotent)
        try:
            db.create_all()
            print("Verified all database tables exist.")
        except Exception as e:
            print(f"Error during db.create_all(): {e}")
            
        # 3. Seed HSN Master if empty
        try:
            from services.hsn_service import seed_hsn_master
            seed_hsn_master()
            print("Successfully seeded HSN Master data.")
        except Exception as e:
            print(f"Error seeding HSN Master: {e}")

        print("Migration complete!")

if __name__ == "__main__":
    run_migration()
