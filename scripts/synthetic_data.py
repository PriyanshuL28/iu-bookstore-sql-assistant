"""Deterministic synthetic data for the IU Bookstore database.

Everything here is made up: names, ISBNs, titles, prices and sales are generated
from a fixed random seed so the dataset (and evaluation answers) are reproducible.
"""

from __future__ import annotations

import bisect
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

START_DATE = date(2024, 7, 1)
END_DATE = date(2026, 9, 30)

CATEGORIES = [
    (1, "Books", "Textbooks for IU courses and general-interest books."),
    (2, "Clothing", "Hoosier apparel: t-shirts, hoodies, jerseys, jackets and more."),
    (3, "Merchandise", "Drinkware, headwear, accessories and gifts."),
    (4, "Flags & Banners", "Flags, banners and pennants for dorms, homes and tailgates."),
]
BOOKS, CLOTHING, MERCH, FLAGS = 1, 2, 3, 4

DESIGNS = [
    "Indiana Hoosiers Arch", "IU Trident Logo", "Hoosiers Basketball", "Indiana Football",
    "Indiana Alumni", "IU Mom", "IU Dad", "Bloomington Script", "Vintage IU", "Little 500",
    "Hoosiers Wordmark", "IU Est. 1820", "Hoosier Nation", "Sample Gates", "Crimson & Cream",
]
COLORS = ["Crimson", "Cream", "White", "Black", "Heather Gray"]
ADULT_SIZES = ["XS", "S", "M", "L", "XL", "2XL", "3XL"]
WOMEN_SIZES = ["XS", "S", "M", "L", "XL", "2XL"]
YOUTH_SIZES = ["YS", "YM", "YL"]
SIZE_POPULARITY = {
    "XS": 0.5, "S": 1.2, "M": 2.0, "L": 2.0, "XL": 1.3, "2XL": 0.6, "3XL": 0.3,
    "YS": 0.8, "YM": 1.0, "YL": 0.8,
}

# product_type: (brands, price range, number of products, fits)
CLOTHING_TYPES = {
    "T-Shirt": (["Nike", "Champion", "Colosseum", "League", "Adidas"], (22, 34), 18, ["Men", "Women", "Unisex", "Youth"]),
    "Hoodie": (["Nike", "Champion", "Under Armour", "Colosseum"], (55, 75), 12, ["Men", "Women", "Unisex", "Youth"]),
    "Jersey": (["Nike", "Adidas"], (75, 130), 6, ["Men", "Women", "Youth"]),
    "Jacket": (["Nike", "Columbia", "Under Armour", "Colosseum"], (85, 160), 7, ["Men", "Women"]),
    "Sweatpants": (["Champion", "Nike", "League"], (45, 60), 5, ["Men", "Women", "Unisex"]),
    "Polo": (["Nike", "Under Armour", "Antigua"], (55, 80), 5, ["Men", "Women"]),
}
JERSEY_NAMES = [
    "#1 Replica Basketball Jersey", "#5 Replica Basketball Jersey", "#24 Replica Basketball Jersey",
    "#2 Replica Football Jersey", "#7 Replica Football Jersey", "Throwback 1987 Basketball Jersey",
]
JACKET_STYLES = ["Quarter-Zip Pullover", "Full-Zip Windbreaker", "Puffer Jacket", "Rain Jacket", "Fleece Jacket", "Varsity Jacket", "Softshell Jacket"]

MERCH_TYPES = {
    "Mug": (["Spirit Products", "RFSJ"], (14, 20), ["IU Trident Coffee Mug", "Hoosiers Travel Mug", "IU Alumni Mug", "Bloomington Camp Mug"]),
    "Water Bottle": (["Hydro Flask", "Yeti", "Spirit Products"], (18, 45), ["IU Insulated Bottle 32oz", "Hoosiers Sport Bottle", "IU Trident Tumbler 20oz"]),
    "Cap": (["Nike", "'47", "Top of the World"], (25, 36), ["IU Trident Dad Hat", "Hoosiers Snapback", "Indiana Fitted Cap", "IU Bucket Hat"]),
    "Beanie": (["Nike", "'47"], (22, 30), ["IU Cuffed Knit Beanie", "Hoosiers Pom Beanie"]),
    "Keychain": (["Spirit Products", "Jardine"], (6, 12), ["IU Trident Metal Keychain", "Sample Gates Keychain", "Hoosiers Bottle Opener Keychain"]),
    "Sticker": (["Blue 84", "Spirit Products"], (3, 7), ["IU Trident Decal", "Hoosiers Laptop Sticker Pack", "Little 500 Bike Sticker"]),
    "Backpack": (["JanSport", "Nike"], (45, 85), ["IU Campus Backpack", "Hoosiers Laptop Backpack"]),
    "Lanyard": (["Rico Industries"], (8, 12), ["IU Lanyard with ID Holder", "Hoosiers Breakaway Lanyard"]),
    "Blanket": (["Pegasus", "Northwest Co."], (40, 70), ["IU Sherpa Throw Blanket", "Hoosiers Stadium Blanket"]),
}

# product_type: (brands, price range, names, sizes)
FLAG_TYPES = {
    "Flag": (["WinCraft", "Collegiate Pacific"], (25, 45), ["IU Trident House Flag", "Indiana Hoosiers Double-Sided Flag", "IU Alumni Flag", "Hoosiers Basketball Banners Flag"], ["3x5 ft", "2x3 ft"]),
    "Banner": (["WinCraft"], (30, 60), ["IU Dorm Room Banner", "Five-Time National Champions Banner", "Indiana Wordmark Wall Banner"], [None]),
    "Pennant": (["Collegiate Pacific"], (12, 20), ["Vintage IU Felt Pennant", "Hoosiers Pennant 12x30"], [None]),
    "Car Flag": (["Rico Industries"], (14, 22), ["IU Trident Car Flag", "Hoosiers Window Car Flag"], [None]),
    "Garden Flag": (["WinCraft", "Evergreen"], (16, 28), ["IU Graduation Garden Flag", "Hoosiers Garden Flag"], ["12x18 in"]),
}

COURSES = [
    ("CSCI-C 200", "Introduction to Computers and Programming", "Luddy School of Informatics, Computing, and Engineering", "Programming with Python"),
    ("CSCI-C 211", "Introduction to Computer Science", "Luddy School of Informatics, Computing, and Engineering", "Computer Science"),
    ("CSCI-C 343", "Data Structures", "Luddy School of Informatics, Computing, and Engineering", "Data Structures and Algorithms"),
    ("CSCI-B 461", "Database Concepts", "Luddy School of Informatics, Computing, and Engineering", "Database Systems"),
    ("INFO-I 101", "Introduction to Informatics", "Luddy School of Informatics, Computing, and Engineering", "Informatics"),
    ("ENGR-E 110", "Engineering in the Modern World", "Luddy School of Informatics, Computing, and Engineering", "Engineering Design"),
    ("BUS-K 201", "The Computer in Business", "Kelley School of Business", "Business Analytics with Excel"),
    ("BUS-A 100", "Basic Accounting Skills", "Kelley School of Business", "Accounting"),
    ("BUS-F 370", "Integrated Business Core - Finance", "Kelley School of Business", "Corporate Finance"),
    ("BUS-M 370", "Integrated Business Core - Marketing", "Kelley School of Business", "Marketing Management"),
    ("BUS-L 201", "Legal Environment of Business", "Kelley School of Business", "Business Law"),
    ("ECON-E 201", "Introduction to Microeconomics", "College of Arts and Sciences", "Microeconomics"),
    ("ECON-E 202", "Introduction to Macroeconomics", "College of Arts and Sciences", "Macroeconomics"),
    ("MATH-M 211", "Calculus I", "College of Arts and Sciences", "Calculus"),
    ("MATH-M 212", "Calculus II", "College of Arts and Sciences", "Calculus: Early Transcendentals"),
    ("STAT-S 301", "Applied Statistical Methods for Business", "College of Arts and Sciences", "Business Statistics"),
    ("PSY-P 101", "Introductory Psychology I", "College of Arts and Sciences", "Psychology"),
    ("BIOL-L 112", "Foundations of Biology: Biological Mechanisms", "College of Arts and Sciences", "Biology"),
    ("CHEM-C 117", "Principles of Chemistry and Biochemistry I", "College of Arts and Sciences", "Chemistry"),
    ("PHYS-P 221", "Physics I", "College of Arts and Sciences", "Physics"),
    ("ENG-W 131", "Reading, Writing, and Inquiry", "College of Arts and Sciences", "Academic Writing"),
    ("HIST-H 105", "American History I", "College of Arts and Sciences", "American History"),
    ("SPAN-S 100", "Elementary Spanish I", "College of Arts and Sciences", "Spanish"),
    ("SPH-H 263", "Personal Health", "School of Public Health", "Personal Health"),
    ("SPH-K 101", "Introduction to Kinesiology", "School of Public Health", "Kinesiology"),
    ("SPEA-V 160", "National and International Policy", "O'Neill School of Public and Environmental Affairs", "Public Policy"),
    ("SPEA-E 162", "Environment and People", "O'Neill School of Public and Environmental Affairs", "Environmental Science"),
    ("MSCH-C 101", "Media", "The Media School", "Mass Media"),
    ("MUS-T 109", "Rudiments of Music I", "Jacobs School of Music", "Music Theory"),
    ("EDUC-P 254", "Educational Psychology for Teachers", "School of Education", "Educational Psychology"),
]
SCHOOLS = sorted({c[2] for c in COURSES})

TEXTBOOK_PUBLISHERS = ["Pearson", "McGraw Hill", "Cengage", "Wiley", "Oxford University Press", "W. W. Norton", "Macmillan Learning", "O'Reilly Media"]
TEXTBOOK_PREFIXES = ["Foundations of", "Principles of", "Essentials of", "Introduction to", "Understanding", "Modern", "Fundamentals of"]
GENERAL_BOOKS = [
    "Hoosier Hysteria: A History of Indiana Basketball", "Bloomington Then and Now", "The Little 500 Story",
    "IU Coloring Book", "Crimson Traditions: 200 Years of Indiana University", "Hoosiers Tailgate Cookbook",
    "Herman B Wells: A Life", "Walking Tour of the IU Campus", "Breaking Away: The Making of a Classic",
    "Indiana State Parks Guide", "Assembly Hall Memories", "The Sample Gates Photo Book",
    "Kinsey: The Institute and Its Legacy", "Hoosier Football Legends", "Bloomington Food & Drink Guide",
]

FIRST_NAMES = [
    "Aiden", "Olivia", "Liam", "Emma", "Noah", "Ava", "Ethan", "Sophia", "Mason", "Isabella", "Lucas", "Mia",
    "Logan", "Charlotte", "Jacob", "Amelia", "Jackson", "Harper", "Elijah", "Evelyn", "Caleb", "Abigail",
    "Wyatt", "Ella", "Owen", "Grace", "Carter", "Chloe", "Henry", "Lily", "Priya", "Arjun", "Wei", "Mei",
    "Hiro", "Yuna", "Carlos", "Sofia", "Diego", "Valentina", "Omar", "Layla", "Tyler", "Madison", "Brandon",
    "Hannah", "Jordan", "Taylor", "Kevin", "Rachel", "Andre", "Jasmine", "Ravi", "Ananya", "Min-jun", "Ji-woo",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Martin", "Jackson", "Thompson", "White", "Harris", "Clark", "Lewis", "Walker",
    "Hall", "Young", "King", "Wright", "Scott", "Green", "Baker", "Adams", "Nelson", "Hill", "Campbell",
    "Mitchell", "Patel", "Shah", "Kumar", "Chen", "Wang", "Li", "Kim", "Park", "Nguyen", "Garcia",
    "Martinez", "Rodriguez", "Lopez", "Hernandez", "Schmidt", "Mueller", "Sullivan", "O'Brien", "Murphy",
]
# Indiana-heavy, Midwest-weighted address states.
STATES = ["IN"] * 55 + ["IL"] * 12 + ["OH"] * 8 + ["MI"] * 5 + ["KY"] * 5 + ["NY", "CA", "TX", "FL", "PA", "WI", "MN", "MO", "GA", "NJ", "WA", "CO", "MD", "VA", "NC"]

CUSTOMER_TYPES = ["Student", "Faculty/Staff", "Alumni", "Visitor"]
CUSTOMER_TYPE_WEIGHTS = [0.55, 0.10, 0.20, 0.15]

PROMOTIONS = [
    ("Back to School", 10, date(2024, 8, 10), date(2024, 8, 31), BOOKS),
    ("Homecoming Week", 20, date(2024, 10, 14), date(2024, 10, 20), CLOTHING),
    ("Black Friday", 25, date(2024, 11, 29), date(2024, 12, 2), None),
    ("Holiday Gift Sale", 15, date(2024, 12, 9), date(2024, 12, 22), MERCH),
    ("Spring Textbook Rush", 10, date(2025, 1, 6), date(2025, 1, 19), BOOKS),
    ("Little 500 Weekend", 15, date(2025, 4, 24), date(2025, 4, 27), CLOTHING),
    ("Graduation Celebration", 20, date(2025, 5, 1), date(2025, 5, 10), FLAGS),
    ("Back to School", 10, date(2025, 8, 9), date(2025, 8, 31), BOOKS),
    ("Homecoming Week", 20, date(2025, 10, 13), date(2025, 10, 19), CLOTHING),
    ("Black Friday", 25, date(2025, 11, 28), date(2025, 12, 1), None),
    ("Holiday Gift Sale", 15, date(2025, 12, 8), date(2025, 12, 21), MERCH),
    ("Spring Textbook Rush", 10, date(2026, 1, 5), date(2026, 1, 18), BOOKS),
    ("Little 500 Weekend", 15, date(2026, 4, 23), date(2026, 4, 26), CLOTHING),
    ("Graduation Celebration", 20, date(2026, 5, 1), date(2026, 5, 10), FLAGS),
    ("Back to School", 10, date(2026, 8, 8), date(2026, 8, 30), BOOKS),
]

# Home football Saturdays (Memorial Stadium) and marquee basketball dates (Assembly Hall).
FOOTBALL_HOME_GAMES = [
    date(2024, 8, 30), date(2024, 9, 7), date(2024, 9, 14), date(2024, 10, 5), date(2024, 10, 19),
    date(2024, 11, 2), date(2024, 11, 9),
    date(2025, 8, 30), date(2025, 9, 6), date(2025, 9, 13), date(2025, 10, 4), date(2025, 10, 18),
    date(2025, 11, 1), date(2025, 11, 15),
    date(2026, 9, 5), date(2026, 9, 12), date(2026, 9, 26),
]
BASKETBALL_HOME_GAMES = [
    date(2024, 11, 16), date(2024, 12, 7), date(2025, 1, 11), date(2025, 1, 25), date(2025, 2, 8),
    date(2025, 2, 22), date(2025, 3, 8),
    date(2025, 11, 15), date(2025, 12, 6), date(2026, 1, 10), date(2026, 1, 24), date(2026, 2, 7),
    date(2026, 2, 21), date(2026, 3, 7),
]


@dataclass
class Dataset:
    categories: list[tuple] = field(default_factory=list)
    products: list[tuple] = field(default_factory=list)
    product_variants: list[tuple] = field(default_factory=list)
    books: list[tuple] = field(default_factory=list)
    courses: list[tuple] = field(default_factory=list)
    course_textbooks: list[tuple] = field(default_factory=list)
    customers: list[tuple] = field(default_factory=list)
    promotions: list[tuple] = field(default_factory=list)
    orders: list[tuple] = field(default_factory=list)
    order_items: list[tuple] = field(default_factory=list)


COLUMNS = {
    "categories": ["category_id", "name", "description"],
    "products": ["product_id", "sku", "name", "category_id", "product_type", "brand", "fit", "unit_price", "unit_cost", "is_active", "created_at"],
    "product_variants": ["variant_id", "product_id", "size", "color", "stock_quantity", "reorder_level"],
    "books": ["product_id", "isbn", "author", "publisher", "edition", "format", "publication_year"],
    "courses": ["course_code", "course_name", "school"],
    "course_textbooks": ["course_code", "product_id", "is_required"],
    "customers": ["customer_id", "first_name", "last_name", "email", "customer_type", "iu_school", "state", "joined_date"],
    "promotions": ["promotion_id", "name", "discount_pct", "start_date", "end_date", "category_id"],
    "orders": ["order_id", "customer_id", "order_date", "channel", "payment_method", "status"],
    "order_items": ["order_item_id", "order_id", "variant_id", "quantity", "unit_price", "discount_pct", "promotion_id"],
}
LOAD_ORDER = list(COLUMNS)


def _price(rng: random.Random, low: float, high: float) -> float:
    return round(rng.uniform(low, high)) - 0.01


def _isbn(rng: random.Random) -> str:
    digits = [9, 7, 8] + [rng.randint(0, 9) for _ in range(9)]
    check = (10 - sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits)) % 10) % 10
    return "".join(map(str, digits + [check]))


class _Builder:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.data = Dataset()
        self.product_id = 0
        self.variant_id = 0
        # category_id -> list of (variant_id, product_id, unit_price, weight)
        self.sellable: dict[int, list[tuple[int, int, float, float]]] = {c[0]: [] for c in CATEGORIES}

    def add_product(self, name, category_id, product_type, brand, fit, low, high, variants):
        rng = self.rng
        self.product_id += 1
        pid = self.product_id
        price = _price(rng, low, high)
        cost = round(price * rng.uniform(0.40, 0.62), 2)
        is_active = rng.random() > 0.05
        created = START_DATE - timedelta(days=rng.randint(30, 900))
        sku = f"IU-{category_id}{pid:04d}"
        self.data.products.append((pid, sku, name, category_id, product_type, brand, fit, price, cost, is_active, created))

        popularity = rng.lognormvariate(0, 0.7)
        for size, color in variants:
            self.variant_id += 1
            size_weight = SIZE_POPULARITY.get(size, 1.0)
            reorder = rng.choice([5, 10, 15, 20])
            if not is_active:
                stock = 0
            elif rng.random() < 0.1:
                stock = rng.randint(0, reorder)
            else:
                stock = int(rng.randint(15, 120) * size_weight)
            self.data.product_variants.append((self.variant_id, pid, size, color, stock, reorder))
            self.sellable[category_id].append((self.variant_id, pid, price, popularity * size_weight))
        return pid

    def build_catalog(self):
        rng = self.rng
        self.data.categories = list(CATEGORIES)
        self.data.courses = [c[:3] for c in COURSES]

        for ptype, (brands, (low, high), count, fits) in CLOTHING_TYPES.items():
            designs = rng.sample(DESIGNS, k=min(count, len(DESIGNS)))
            for i in range(count):
                fit = fits[i % len(fits)]
                if ptype == "Jersey":
                    name = f"{fit}'s {JERSEY_NAMES[i % len(JERSEY_NAMES)]}" if fit != "Youth" else f"Youth {JERSEY_NAMES[i % len(JERSEY_NAMES)]}"
                    colors = ["Crimson"] if i % 2 == 0 else ["White"]
                elif ptype == "Jacket":
                    name = f"{fit}'s IU {JACKET_STYLES[i % len(JACKET_STYLES)]}"
                    colors = rng.sample(["Crimson", "Black", "Heather Gray"], k=rng.randint(1, 2))
                else:
                    design = designs[i % len(designs)]
                    prefix = "Youth" if fit == "Youth" else f"{fit}'s" if fit in ("Men", "Women") else "Unisex"
                    name = f"{prefix} {design} {ptype}"
                    colors = rng.sample(COLORS, k=rng.randint(1, 3))
                sizes = YOUTH_SIZES if fit == "Youth" else WOMEN_SIZES if fit == "Women" else ADULT_SIZES
                variants = [(s, c) for c in colors for s in sizes]
                if fit == "Youth":
                    low_, high_ = low * 0.75, high * 0.8
                else:
                    low_, high_ = low, high
                self.add_product(name, CLOTHING, ptype, rng.choice(brands), fit, low_, high_, variants)

        for ptype, (brands, (low, high), names) in MERCH_TYPES.items():
            for name in names:
                colors = [None] if ptype in ("Sticker", "Keychain") else [rng.choice(["Crimson", "White", "Black"])]
                self.add_product(name, MERCH, ptype, rng.choice(brands), None, low, high, [(None, c) for c in colors])

        for ptype, (brands, (low, high), names, sizes) in FLAG_TYPES.items():
            for name in names:
                self.add_product(name, FLAGS, ptype, rng.choice(brands), None, low, high, [(s, "Crimson") for s in sizes])

        used_titles = set()
        for code, _course_name, _school, subject in COURSES:
            prefixes = rng.sample(TEXTBOOK_PREFIXES, k=2)
            for n in range(rng.choice([1, 1, 2])):
                title = f"{prefixes[n]} {subject}"
                if title in used_titles:
                    title = f"{title}: A Practical Approach"
                used_titles.add(title)
                edition = rng.randint(2, 12)
                pid = self.add_product(f"{title}, {edition}e", BOOKS, "Textbook", rng.choice(TEXTBOOK_PUBLISHERS), None, 60, 260, [(None, None)])
                publisher = self.data.products[-1][5]
                author = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
                if rng.random() < 0.4:
                    author += f" and {rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
                fmt = rng.choice(["Hardcover", "Paperback", "Loose-leaf"])
                self.data.books.append((pid, _isbn(rng), author, publisher, edition, fmt, rng.randint(2015, 2025)))
                self.data.course_textbooks.append((code, pid, n == 0 or rng.random() < 0.3))

        for title in GENERAL_BOOKS:
            pid = self.add_product(title, BOOKS, "General Book", "IU Press", None, 15, 40, [(None, None)])
            author = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
            fmt = rng.choice(["Hardcover", "Paperback"])
            self.data.books.append((pid, _isbn(rng), author, "IU Press", None, fmt, rng.randint(2005, 2025)))

        # Students mostly buy textbooks for courses in their own school.
        self.textbooks_by_school: dict[str, list[tuple]] = {s: [] for s in SCHOOLS}
        school_of = {c[0]: c[2] for c in COURSES}
        textbook_ids = {ct[1]: school_of[ct[0]] for ct in self.data.course_textbooks}
        for item in self.sellable[BOOKS]:
            if item[1] in textbook_ids:
                self.textbooks_by_school[textbook_ids[item[1]]].append(item)

    def build_customers(self, count: int = 3000):
        rng = self.rng
        span = (END_DATE - date(2019, 1, 1)).days
        rows = []
        for _ in range(count):
            first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
            ctype = rng.choices(CUSTOMER_TYPES, CUSTOMER_TYPE_WEIGHTS)[0]
            school = rng.choice(SCHOOLS) if ctype == "Student" else None
            state = "IN" if ctype in ("Student", "Faculty/Staff") and rng.random() < 0.6 else rng.choice(STATES)
            # Skew sign-ups toward earlier years so there is an established base when sales begin.
            joined = date(2019, 1, 1) + timedelta(days=int(span * rng.random() ** 1.6))
            rows.append([first, last, ctype, school, state, joined])
        rows.sort(key=lambda r: r[5])
        for cid, (first, last, ctype, school, state, joined) in enumerate(rows, start=1):
            handle = f"{first}.{last}".lower().replace("'", "").replace("-", "")
            domain = "iu.edu" if ctype in ("Student", "Faculty/Staff") else rng.choice(["gmail.com", "yahoo.com", "outlook.com", "icloud.com"])
            self.data.customers.append((cid, first, last, f"{handle}{cid}@{domain}", ctype, school, state, joined))
        self.customer_join_dates = [c[7] for c in self.data.customers]

    def build_promotions(self):
        self.data.promotions = [(i, *p) for i, p in enumerate(PROMOTIONS, start=1)]

    def _day_profile(self, day: date) -> tuple[float, dict[int, float], str | None]:
        """Order volume multiplier, category mix and special event for a day."""
        mult = 1.0
        mix = {CLOTHING: 0.40, MERCH: 0.25, BOOKS: 0.20, FLAGS: 0.15}
        event = None
        m, d = day.month, day.day
        if day.weekday() >= 5:
            mult *= 1.2
        if m in (6, 7):
            mult *= 0.5
        if (m == 8 and d >= 10) or (m == 9 and d <= 10) or (m == 1 and 4 <= d <= 25):
            mult *= 2.8
            mix = {BOOKS: 0.60, CLOTHING: 0.22, MERCH: 0.12, FLAGS: 0.06}
            event = "textbook_rush"
        if m == 12 and d <= 23:
            mult *= 1.6
            mix = {CLOTHING: 0.42, MERCH: 0.38, BOOKS: 0.10, FLAGS: 0.10}
            event = "holiday"
        if m == 4 and 20 <= d <= 27:
            mult *= 1.8
            event = "little500"
        if m == 5 and d <= 10:
            mult *= 2.5
            mix = {FLAGS: 0.30, MERCH: 0.30, CLOTHING: 0.32, BOOKS: 0.08}
            event = "graduation"
        if day in FOOTBALL_HOME_GAMES:
            mult *= 4.0
            mix = {CLOTHING: 0.50, MERCH: 0.30, FLAGS: 0.17, BOOKS: 0.03}
            event = "football"
        elif day in BASKETBALL_HOME_GAMES:
            mult *= 2.5
            mix = {CLOTHING: 0.50, MERCH: 0.30, FLAGS: 0.17, BOOKS: 0.03}
            event = "basketball"
        return mult, mix, event

    def _pick_customer(self, day: date, preferred: str | None) -> tuple:
        eligible = bisect.bisect_right(self.customer_join_dates, day)
        customer = self.data.customers[self.rng.randrange(eligible)]
        for _ in range(4):
            if preferred is None or customer[4] == preferred:
                break
            customer = self.data.customers[self.rng.randrange(eligible)]
        return customer

    def _active_promotion(self, day: date, category_id: int):
        for promo in self.data.promotions:
            pid, _name, pct, start, end, cat = promo
            if start <= day <= end and (cat is None or cat == category_id):
                return pid, pct
        return None, 0

    def build_orders(self, base_orders_per_day: float = 6.5):
        rng = self.rng
        order_id = item_id = 0
        day = START_DATE
        while day <= END_DATE:
            mult, mix, event = self._day_profile(day)
            # Year-over-year growth of ~12%.
            growth = 1 + 0.12 * (day - START_DATE).days / 365
            n_orders = max(0, int(rng.gauss(base_orders_per_day * mult * growth, 2)))
            categories, weights = zip(*mix.items())
            for _ in range(n_orders):
                order_id += 1
                game_day = event in ("football", "basketball")
                if game_day:
                    channel = rng.choices(["Game Day Kiosk", "In-Store", "Online"], [0.6, 0.3, 0.1])[0]
                elif event == "holiday":
                    channel = rng.choices(["In-Store", "Online"], [0.4, 0.6])[0]
                else:
                    channel = rng.choices(["In-Store", "Online"], [0.62, 0.38])[0]

                preferred = "Student" if event == "textbook_rush" else "Alumni" if game_day and rng.random() < 0.4 else None
                customer = self._pick_customer(day, preferred)
                ctype, school = customer[4], customer[5]

                if channel == "Online":
                    hour = rng.randint(0, 23)
                    payment = rng.choices(["Credit Card", "Debit Card", "Apple Pay"], [0.6, 0.25, 0.15])[0]
                else:
                    hour = rng.randint(9, 20)
                    options = ["Credit Card", "Debit Card", "Apple Pay", "Cash"]
                    weights_pay = [0.4, 0.25, 0.2, 0.15]
                    if ctype == "Student":
                        options, weights_pay = options + ["CrimsonCard"], [0.25, 0.2, 0.15, 0.05, 0.35]
                    payment = rng.choices(options, weights_pay)[0]
                ts = datetime(day.year, day.month, day.day, hour, rng.randint(0, 59), rng.randint(0, 59))
                status = "Refunded" if rng.random() < 0.03 else "Completed"
                self.data.orders.append((order_id, customer[0], ts, channel, payment, status))

                n_lines = rng.choices([1, 2, 3, 4], [0.5, 0.3, 0.15, 0.05])[0]
                chosen = set()
                for _ in range(n_lines):
                    cat = rng.choices(categories, weights)[0]
                    pool = self.sellable[cat]
                    if cat == BOOKS and ctype == "Student" and school and rng.random() < 0.8 and self.textbooks_by_school.get(school):
                        pool = self.textbooks_by_school[school]
                    variant_id, _pid, price, _w = rng.choices(pool, [p[3] for p in pool])[0]
                    if variant_id in chosen:
                        continue
                    chosen.add(variant_id)
                    if cat == BOOKS:
                        qty = 1
                    else:
                        qty = rng.choices([1, 2, 3, 4], [0.7, 0.2, 0.07, 0.03])[0]
                    promo_id, pct = self._active_promotion(day, cat)
                    item_id += 1
                    self.data.order_items.append((item_id, order_id, variant_id, qty, price, pct, promo_id))
            day += timedelta(days=1)


def generate(seed: int = 42) -> Dataset:
    builder = _Builder(seed)
    builder.build_catalog()
    builder.build_customers()
    builder.build_promotions()
    builder.build_orders()
    return builder.data
