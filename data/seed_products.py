"""Seed categories, sample parties, ledger groups and 50+50 products."""
import random
from extensions import db
from models import Category, Product, Party, Ledger, User, ROLE_MASTER, ROLE_ADMIN, ROLE_USER
from services.hsn_service import best_match


COMPUTER_PARTS = [
    ("Intel Core i5-13400 Processor", "computer", "cpu processor"),
    ("Intel Core i7-13700K Processor", "computer", "cpu processor"),
    ("Intel Core i9-13900K Processor", "computer", "cpu processor"),
    ("AMD Ryzen 5 7600 Processor", "computer", "cpu processor"),
    ("AMD Ryzen 7 7700X Processor", "computer", "cpu processor"),
    ("AMD Ryzen 9 7950X Processor", "computer", "cpu processor"),
    ("ASUS Prime B760M Motherboard", "computer", "motherboard"),
    ("MSI MAG B650 Tomahawk Motherboard", "computer", "motherboard"),
    ("Gigabyte Z790 AORUS Elite Motherboard", "computer", "motherboard"),
    ("ASRock B550M Steel Legend Motherboard", "computer", "motherboard"),
    ("Corsair Vengeance 16GB DDR4 3200MHz RAM", "computer", "ram memory ddr4"),
    ("Kingston Fury 32GB DDR5 5600MHz RAM", "computer", "ram memory ddr5"),
    ("G.Skill Trident Z 16GB DDR4 3600 RAM", "computer", "ram memory ddr4"),
    ("Crucial 8GB DDR4 SODIMM Laptop RAM", "computer", "ram memory laptop"),
    ("Samsung 980 Pro 1TB NVMe SSD", "computer", "ssd nvme storage"),
    ("WD Black SN850X 2TB NVMe SSD", "computer", "ssd nvme storage"),
    ("Crucial MX500 500GB SATA SSD", "computer", "ssd storage"),
    ("Seagate Barracuda 2TB HDD", "computer", "hard disk drive hdd"),
    ("WD Blue 4TB HDD", "computer", "hard disk drive hdd"),
    ("NVIDIA RTX 4070 Graphics Card", "computer", "graphics card gpu"),
    ("NVIDIA RTX 4090 Founders Edition", "computer", "graphics card gpu"),
    ("AMD Radeon RX 7800 XT Graphics Card", "computer", "graphics card gpu"),
    ("Corsair RM850x 850W PSU", "computer", "smps power supply psu"),
    ("Cooler Master MWE 650W PSU", "computer", "smps power supply psu"),
    ("APC Back-UPS 600VA", "computer", "ups power"),
    ("APC Smart-UPS 1500VA", "computer", "ups power"),
    ("NZXT H510 ATX Cabinet", "computer", "cabinet chassis case"),
    ("Cooler Master MasterBox NR200P Cabinet", "computer", "cabinet chassis case"),
    ("Logitech MK270 Wireless Keyboard Mouse Combo", "computer", "keyboard mouse"),
    ("Razer BlackWidow V4 Mechanical Keyboard", "computer", "keyboard"),
    ("Logitech G502 HERO Gaming Mouse", "computer", "mouse"),
    ("Dell P2422H 24-inch Monitor", "computer", "monitor lcd led"),
    ("LG UltraGear 27 inch 144Hz Monitor", "computer", "monitor display"),
    ("Samsung Odyssey G7 32 inch Curved Monitor", "computer", "monitor display"),
    ("HP DeskJet 2331 Color Printer", "computer", "printer inkjet"),
    ("Brother HL-L2321D Laser Printer", "computer", "printer laser"),
    ("Canon PIXMA G3010 Multifunction Printer", "computer", "printer mfp"),
    ("TP-Link Archer C6 AC1200 WiFi Router", "computer", "router wifi"),
    ("Netgear Nighthawk AX1800 WiFi 6 Router", "computer", "router wifi"),
    ("D-Link 8-Port Gigabit Switch", "computer", "switch network"),
    ("SanDisk Ultra 64GB USB 3.0 Pen Drive", "computer", "pen drive usb"),
    ("Kingston DataTraveler 128GB Pen Drive", "computer", "pen drive usb"),
    ("WD My Passport 2TB External HDD", "computer", "external hard disk hdd"),
    ("Samsung T7 1TB Portable SSD", "computer", "external ssd"),
    ("Logitech C920 HD Pro Webcam", "computer", "webcam camera"),
    ("Boya BY-M1 Lavalier Microphone", "computer", "microphone mic"),
    ("Sony WH-CH520 Wireless Headphones", "computer", "headphone"),
    ("boAt Rockerz 450 Bluetooth Headset", "computer", "headphone headset"),
    ("Amkette EvoFox Gaming Speakers 2.1", "computer", "speaker"),
    ("Amazon Basics HDMI 2.0 Cable 2m", "computer", "hdmi cable"),
]

HOME_APPLIANCES = [
    ("LG 260L Double Door Refrigerator", "home", "refrigerator double door"),
    ("Samsung 198L Single Door Refrigerator", "home", "refrigerator single door"),
    ("Whirlpool 240L Double Door Frost Free Fridge", "home", "refrigerator double door"),
    ("Haier 165L Single Door Refrigerator", "home", "refrigerator"),
    ("Godrej 190L Single Door Refrigerator", "home", "refrigerator"),
    ("LG 7Kg Front Load Fully Automatic Washing Machine", "home", "washing machine front load"),
    ("Samsung 6.5Kg Top Load Fully Automatic Washer", "home", "washing machine top load"),
    ("IFB 7Kg Senator Smart Touch Front Load WM", "home", "washing machine"),
    ("Whirlpool 7.5Kg Semi Automatic Washing Machine", "home", "washing machine semi automatic"),
    ("Bosch 8Kg Front Load Washer Dryer", "home", "washing machine front load"),
    ("Daikin 1.5 Ton 5 Star Inverter Split AC", "home", "split ac inverter"),
    ("LG 1 Ton 3 Star Inverter Split AC", "home", "split ac inverter"),
    ("Voltas 1.5 Ton 3 Star Window AC", "home", "window ac"),
    ("Carrier 2 Ton Cassette AC", "home", "cassette ac"),
    ("Hitachi 1.5 Ton 5 Star Split AC", "home", "split ac"),
    ("Bajaj Majesty New Shakti 25L Storage Geyser", "home", "geyser water heater storage"),
    ("AO Smith 15L Instant Water Geyser", "home", "geyser instant"),
    ("Havells Instanio 3L Water Heater", "home", "geyser instant"),
    ("Philips GC1905 1440W Steam Iron", "home", "iron steam"),
    ("Bajaj DX-7 1000W Dry Iron", "home", "iron dry"),
    ("Prestige PIC 20 Induction Cooktop", "home", "induction cooktop"),
    ("Pigeon Stovekraft 2 Burner Gas Stove", "home", "gas stove burner"),
    ("Sunflame 3 Burner Glass Top Cooktop", "home", "gas stove burner"),
    ("Prestige Marvel Plus 1.5L Electric Kettle", "home", "electric kettle"),
    ("Pigeon 1.5L Stainless Steel Kettle", "home", "electric kettle"),
    ("Morphy Richards 2 Slice Pop-up Toaster", "home", "toaster"),
    ("Philips HD2582 Pop-up Toaster", "home", "toaster"),
    ("IFB 23L Convection Microwave Oven", "home", "microwave oven convection"),
    ("LG 28L Convection Microwave Oven", "home", "microwave oven"),
    ("Samsung 23L Solo Microwave Oven", "home", "microwave oven solo"),
    ("Bajaj Majesty 1603T OTG Oven 16L", "home", "otg oven"),
    ("Eureka Forbes Quick Clean Vacuum Cleaner", "home", "vacuum cleaner"),
    ("Mi Robot Vacuum-Mop 2 Pro", "home", "vacuum cleaner robot"),
    ("Bajaj Rex 500W Mixer Grinder", "home", "mixer grinder"),
    ("Philips HL7756 750W Mixer Grinder", "home", "mixer grinder"),
    ("Preethi Zodiac 750W Mixer Grinder", "home", "mixer grinder"),
    ("Sujata Powermatic Plus 900W Mixer Grinder", "home", "mixer grinder"),
    ("Bajaj JEX 16 500W Centrifugal Juicer", "home", "juicer"),
    ("Usha 1200mm Striker Ceiling Fan", "home", "ceiling fan"),
    ("Crompton Hill Briz 1200mm Ceiling Fan", "home", "ceiling fan"),
    ("Havells Velocity 400mm Table Fan", "home", "table fan"),
    ("Bajaj Esteem 400mm Pedestal Fan", "home", "pedestal fan"),
    ("Atomberg Studio+ BLDC Ceiling Fan", "home", "ceiling fan"),
    ("Kent Grand Plus 8L RO Water Purifier", "home", "water purifier ro"),
    ("Aquaguard Marvel NXT RO+UV+UF Purifier", "home", "water purifier ro uv"),
    ("Pureit Classic G2 Water Purifier", "home", "water purifier"),
    ("LG 8 Place Settings Dishwasher", "home", "dishwasher"),
    ("Bosch 12 Place Settings Dishwasher", "home", "dishwasher"),
    ("Samsung 55 inch 4K UHD Smart TV", "home", "television tv"),
    ("OnePlus Y1S 43 inch Full HD Smart TV", "home", "television tv"),
]


def _slug(s):
    return "".join(ch for ch in s.upper() if ch.isalnum())[:24]


def seed_all():
    # ---- Categories ----
    cats = {}
    for cname, hsn, gst in [
        ("Computer & Laptops", "8471", 18),
        ("Computer Parts", "8473", 18),
        ("Computer Peripherals", "8471", 18),
        ("Networking", "8517", 18),
        ("Storage Media", "8523", 18),
        ("Printers & Scanners", "8443", 18),
        ("Audio & Video", "8518", 18),
        ("Home Refrigeration", "8418", 28),
        ("Washing Machines", "8450", 28),
        ("Air Conditioners", "8415", 28),
        ("Kitchen Appliances", "8516", 18),
        ("Small Home Appliances", "8509", 18),
        ("Fans & Coolers", "8414", 18),
        ("Television", "8528", 18),
        ("Water Purifiers", "8419", 18),
    ]:
        c = Category.query.filter_by(name=cname).first() or Category(name=cname)
        c.default_hsn = hsn; c.default_gst_rate = gst
        db.session.merge(c)
        cats[cname] = c
    db.session.flush()

    # ---- Products ----
    def _cat_for(name, kind):
        n = name.lower()
        if kind == "computer":
            if "monitor" in n: return cats["Computer Peripherals"]
            if "router" in n or "switch" in n or "wifi" in n: return cats["Networking"]
            if "ssd" in n or "hdd" in n or "pen drive" in n or "passport" in n: return cats["Storage Media"]
            if "printer" in n: return cats["Printers & Scanners"]
            if "headphone" in n or "speaker" in n or "headset" in n or "mic" in n: return cats["Audio & Video"]
            if "laptop" in n or "notebook" in n: return cats["Computer & Laptops"]
            if "keyboard" in n or "mouse" in n or "webcam" in n or "hdmi" in n: return cats["Computer Peripherals"]
            return cats["Computer Parts"]
        if kind == "home":
            if "refrigerator" in n or "fridge" in n: return cats["Home Refrigeration"]
            if "washing" in n or "washer" in n: return cats["Washing Machines"]
            if "ac" in n.split() or "split ac" in n or "window ac" in n or "cassette" in n: return cats["Air Conditioners"]
            if "fan" in n: return cats["Fans & Coolers"]
            if "tv" in n.split() or "television" in n: return cats["Television"]
            if "purifier" in n: return cats["Water Purifiers"]
            if "mixer" in n or "grinder" in n or "juicer" in n or "vacuum" in n: return cats["Small Home Appliances"]
            return cats["Kitchen Appliances"]
        return None

    all_items = [(n, k, kw) for (n, k, kw) in COMPUTER_PARTS + HOME_APPLIANCES]
    for name, kind, kw in all_items:
        sku = _slug(name)
        if Product.query.filter_by(sku=sku).first():
            continue
        match = best_match(kw) or best_match(name) or {}
        cat = _cat_for(name, kind)
        hsn = match.get("hsn") or (cat.default_hsn if cat else "")
        gst = match.get("gst") or (cat.default_gst_rate if cat else 18)
        purchase = random.choice([799, 1499, 2999, 5999, 8999, 12999, 18999, 24999, 34999])
        sale = round(purchase * random.uniform(1.10, 1.25), 0)
        p = Product(
            sku=sku, name=name, category_id=cat.id if cat else None,
            hsn_code=hsn, gst_rate=gst, unit="PCS",
            purchase_price=purchase, sale_price=sale,
            stock_qty=random.randint(5, 50), reorder_level=5,
        )
        db.session.add(p)

    # ---- Parties ----
    for n, t, st, sc in [
        ("Cash", "customer", "Maharashtra", "27"),
        ("Walk-in Customer", "customer", "Maharashtra", "27"),
        ("Sharma Electronics", "customer", "Delhi", "07"),
        ("South Computer Hub", "customer", "Karnataka", "29"),
        ("Mumbai Tech Distributors", "supplier", "Maharashtra", "27"),
        ("Chennai Appliance Co", "supplier", "Tamil Nadu", "33"),
    ]:
        if not Party.query.filter_by(name=n).first():
            db.session.add(Party(name=n, party_type=t, state=st, state_code=sc))

    # ---- Default ledgers (Tally-style chart of accounts) ----
    for name, group in [
        ("Cash", "Cash-in-hand"),
        ("Bank", "Bank Accounts"),
        ("Sales Account", "Sales Accounts"),
        ("Purchase Account", "Purchase Accounts"),
        ("Output CGST", "Duties & Taxes"),
        ("Output SGST", "Duties & Taxes"),
        ("Output IGST", "Duties & Taxes"),
        ("Input CGST", "Duties & Taxes"),
        ("Input SGST", "Duties & Taxes"),
        ("Input IGST", "Duties & Taxes"),
        ("Round Off", "Indirect Expenses"),
        ("Discount Allowed", "Indirect Expenses"),
        ("Discount Received", "Indirect Incomes"),
    ]:
        if not Ledger.query.filter_by(name=name).first():
            db.session.add(Ledger(name=name, group_name=group))

    # ---- Default master_admin user ----
    if not User.query.filter_by(role=ROLE_MASTER).first():
        u = User(username="master", full_name="Master Admin", role=ROLE_MASTER)
        u.set_password("master@123")
        db.session.add(u)
    if not User.query.filter_by(username="admin").first():
        u = User(username="admin", full_name="Admin User", role=ROLE_ADMIN)
        u.set_password("admin@123")
        db.session.add(u)
    if not User.query.filter_by(username="user").first():
        u = User(username="user", full_name="Cashier", role=ROLE_USER)
        u.set_password("user@123")
        db.session.add(u)

    db.session.commit()
