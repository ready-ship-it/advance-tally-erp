"""
Product scraper and import service for major Indian retailers.

Supported retailers:
- Khosla Electronics (khoslaonline.com)
- MDComputers (mdcomputers.in)
- Vedanta Computers (vedantcomputers.com)
- Flipkart (flipkart.com)
- Amazon (amazon.in)
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from extensions import db
from models import Product, Category
from services.hsn_service import search_hsn_by_description


class ProductScraper:
    """Base class for product scrapers."""
    
    def __init__(self, retailer_name):
        self.retailer_name = retailer_name
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.products = []
    
    def fetch_page(self, url):
        """Fetch page content."""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None
    
    def parse_products(self):
        """Parse products from page. Override in subclass."""
        raise NotImplementedError
    
    def get_products(self):
        """Get scraped products."""
        return self.products
    
    def add_product(self, sku, name, category, price, description="", hsn_code=""):
        """Add product to list."""
        # Auto-suggest HSN if not provided
        if not hsn_code:
            hsn_result = search_hsn_by_description(name)
            if hsn_result:
                hsn_code = hsn_result[0].hsn_code
        
        self.products.append({
            "sku": f"{self.retailer_name}_{sku}",
            "name": name,
            "category": category,
            "sale_price": price,
            "description": description,
            "hsn_code": hsn_code,
            "retailer": self.retailer_name,
            "source_url": ""
        })


class KhoslaElectronicsScraper(ProductScraper):
    """Scraper for Khosla Electronics."""
    
    def __init__(self):
        super().__init__("Khosla")
        self.base_url = "https://www.khoslaonline.com"
    
    def scrape_category(self, category_url):
        """Scrape products from a category."""
        page = self.fetch_page(category_url)
        if not page:
            return
        
        soup = BeautifulSoup(page, 'html.parser')
        
        # Note: Actual selectors depend on website structure
        # This is a template - adjust selectors based on actual HTML
        products = soup.find_all('div', class_='product-item')
        
        for product in products:
            try:
                name = product.find('h2', class_='product-name')
                price = product.find('span', class_='product-price')
                
                if name and price:
                    self.add_product(
                        sku=name.text[:20],
                        name=name.text,
                        category="Electronics",
                        price=float(price.text.replace('₹', '').replace(',', '')),
                        description=""
                    )
            except Exception as e:
                print(f"Error parsing product: {str(e)}")


class MDComputersScraper(ProductScraper):
    """Scraper for MDComputers.in."""
    
    def __init__(self):
        super().__init__("MDComputers")
        self.base_url = "https://mdcomputers.in"
    
    def scrape_category(self, category_url):
        """Scrape products from a category."""
        page = self.fetch_page(category_url)
        if not page:
            return
        
        soup = BeautifulSoup(page, 'html.parser')
        
        # Template selectors - adjust based on actual website
        products = soup.find_all('div', class_='product')
        
        for product in products:
            try:
                name = product.find('a', class_='product-name')
                price = product.find('span', class_='price')
                
                if name and price:
                    self.add_product(
                        sku=name.text[:20],
                        name=name.text,
                        category="Computers",
                        price=float(price.text.replace('₹', '').replace(',', '')),
                        description=""
                    )
            except Exception as e:
                print(f"Error parsing product: {str(e)}")


class VedantaComputersScraper(ProductScraper):
    """Scraper for Vedanta Computers."""
    
    def __init__(self):
        super().__init__("Vedanta")
        self.base_url = "https://www.vedantcomputers.com"
    
    def scrape_category(self, category_url):
        """Scrape products from a category."""
        page = self.fetch_page(category_url)
        if not page:
            return
        
        soup = BeautifulSoup(page, 'html.parser')
        
        # Template selectors
        products = soup.find_all('div', class_='item')
        
        for product in products:
            try:
                name = product.find('h3')
                price = product.find('span', class_='amount')
                
                if name and price:
                    self.add_product(
                        sku=name.text[:20],
                        name=name.text,
                        category="Computers",
                        price=float(price.text.replace('₹', '').replace(',', '')),
                        description=""
                    )
            except Exception as e:
                print(f"Error parsing product: {str(e)}")


class FlipkartScraper(ProductScraper):
    """Scraper for Flipkart."""
    
    def __init__(self):
        super().__init__("Flipkart")
        self.base_url = "https://www.flipkart.com"
    
    def scrape_category(self, category_url):
        """Scrape products from Flipkart category."""
        page = self.fetch_page(category_url)
        if not page:
            return
        
        soup = BeautifulSoup(page, 'html.parser')
        
        # Flipkart uses different selectors
        products = soup.find_all('div', {'data-id': True})
        
        for product in products:
            try:
                name = product.find('a', class_='s1Q50')
                price = product.find('div', class_='_30jeq3')
                
                if name and price:
                    self.add_product(
                        sku=product.get('data-id', '')[:20],
                        name=name.text,
                        category="Electronics",
                        price=float(price.text.replace('₹', '').replace(',', '')),
                        description=""
                    )
            except Exception as e:
                print(f"Error parsing product: {str(e)}")


class AmazonScraper(ProductScraper):
    """Scraper for Amazon.in."""
    
    def __init__(self):
        super().__init__("Amazon")
        self.base_url = "https://www.amazon.in"
    
    def scrape_category(self, category_url):
        """Scrape products from Amazon category."""
        page = self.fetch_page(category_url)
        if not page:
            return
        
        soup = BeautifulSoup(page, 'html.parser')
        
        # Amazon uses different selectors
        products = soup.find_all('div', {'data-component-type': 's-search-result'})
        
        for product in products:
            try:
                name = product.find('h2', class_='s-size-mini')
                price = product.find('span', class_='a-price-whole')
                
                if name and price:
                    self.add_product(
                        sku=name.text[:20],
                        name=name.text,
                        category="Electronics",
                        price=float(price.text.replace('₹', '').replace(',', '').replace('.', '')),
                        description=""
                    )
            except Exception as e:
                print(f"Error parsing product: {str(e)}")


def import_products_from_scraper(scraper, category_name="Electronics"):
    """
    Import scraped products to database.
    
    Args:
        scraper: ProductScraper instance
        category_name: Category to assign products to
    """
    # Get or create category
    category = Category.query.filter_by(name=category_name).first()
    if not category:
        category = Category(name=category_name, default_gst_rate=18.0)
        db.session.add(category)
        db.session.commit()
    
    imported_count = 0
    duplicate_count = 0
    error_count = 0
    
    for product_data in scraper.get_products():
        try:
            # Check if product already exists
            existing = Product.query.filter_by(sku=product_data["sku"]).first()
            if existing:
                duplicate_count += 1
                continue
            
            # Create new product
            product = Product(
                sku=product_data["sku"],
                name=product_data["name"],
                category_id=category.id,
                hsn_code=product_data.get("hsn_code", ""),
                gst_rate=18.0,
                unit="PCS",
                sale_price=product_data["sale_price"],
                purchase_price=product_data["sale_price"] * 0.7,  # Estimate 30% margin
                description=product_data.get("description", "")
            )
            
            db.session.add(product)
            imported_count += 1
        
        except Exception as e:
            print(f"Error importing product: {str(e)}")
            error_count += 1
    
    db.session.commit()
    
    return {
        "imported": imported_count,
        "duplicates": duplicate_count,
        "errors": error_count,
        "retailer": scraper.retailer_name
    }


def import_sample_products():
    """Import sample products for testing."""
    sample_products = [
        {
            "sku": "LAPTOP001",
            "name": "Dell Inspiron 15 Laptop",
            "category": "Computers",
            "hsn_code": "8471",
            "gst_rate": 18.0,
            "sale_price": 45000,
            "purchase_price": 32000
        },
        {
            "sku": "GPU001",
            "name": "NVIDIA RTX 4060 Graphics Card",
            "category": "Computer Parts",
            "hsn_code": "8473",
            "gst_rate": 18.0,
            "sale_price": 25000,
            "purchase_price": 18000
        },
        {
            "sku": "MONITOR001",
            "name": "LG 24 inch Full HD Monitor",
            "category": "Display",
            "hsn_code": "8528",
            "gst_rate": 18.0,
            "sale_price": 12000,
            "purchase_price": 8500
        },
        {
            "sku": "KEYBOARD001",
            "name": "Mechanical Gaming Keyboard RGB",
            "category": "Accessories",
            "hsn_code": "8471",
            "gst_rate": 18.0,
            "sale_price": 5000,
            "purchase_price": 3000
        },
        {
            "sku": "MOUSE001",
            "name": "Wireless Mouse Ergonomic",
            "category": "Accessories",
            "hsn_code": "8471",
            "gst_rate": 18.0,
            "sale_price": 1500,
            "purchase_price": 800
        },
        {
            "sku": "AC001",
            "name": "Voltas 1.5 Ton Air Conditioner",
            "category": "Appliances",
            "hsn_code": "8415",
            "gst_rate": 28.0,
            "sale_price": 35000,
            "purchase_price": 25000
        },
        {
            "sku": "PHONE001",
            "name": "Samsung Galaxy A15 Smartphone",
            "category": "Telecom",
            "hsn_code": "8517",
            "gst_rate": 18.0,
            "sale_price": 15000,
            "purchase_price": 10500
        },
        {
            "sku": "SSD001",
            "name": "Samsung 970 EVO Plus 1TB NVMe SSD",
            "category": "Storage Devices",
            "hsn_code": "8523",
            "gst_rate": 18.0,
            "sale_price": 8000,
            "purchase_price": 5500
        }
    ]
    
    imported = 0
    
    for product_data in sample_products:
        # Get or create category
        category = Category.query.filter_by(name=product_data["category"]).first()
        if not category:
            category = Category(
                name=product_data["category"],
                default_gst_rate=product_data.get("gst_rate", 18.0)
            )
            db.session.add(category)
            db.session.commit()
        
        # Check if product exists
        existing = Product.query.filter_by(sku=product_data["sku"]).first()
        if existing:
            continue
        
        # Create product
        product = Product(
            sku=product_data["sku"],
            name=product_data["name"],
            category_id=category.id,
            hsn_code=product_data.get("hsn_code", ""),
            gst_rate=product_data.get("gst_rate", 18.0),
            unit="PCS",
            sale_price=product_data["sale_price"],
            purchase_price=product_data["purchase_price"]
        )
        
        db.session.add(product)
        imported += 1
    
    db.session.commit()
    return imported
