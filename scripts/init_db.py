"""One-shot DB initializer (used locally; Railway calls create_all on startup)."""
from app import create_app
from extensions import db
from data.seed_products import seed_all


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_all()
        print("Database initialized + seeded.")
        print("Default logins:")
        print("  master / master@123")
        print("  admin  / admin@123")
        print("  user   / user@123")


if __name__ == "__main__":
    main()
