-- IU Bookstore (synthetic data) - PostgreSQL / Supabase schema.
-- Tables live in their own schema so they are not exposed through Supabase's public Data API.
-- Column comments are read by the app and sent to the LLM as schema documentation.

DROP SCHEMA IF EXISTS bookstore CASCADE;
CREATE SCHEMA bookstore;
SET search_path TO bookstore;

CREATE TABLE categories (
    category_id  SERIAL PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    description  TEXT
);
COMMENT ON TABLE categories IS 'Top-level store departments.';
COMMENT ON COLUMN categories.name IS 'One of: Books, Clothing, Merchandise, Flags & Banners.';

CREATE TABLE products (
    product_id    SERIAL PRIMARY KEY,
    sku           TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    category_id   INT NOT NULL REFERENCES categories(category_id),
    product_type  TEXT NOT NULL,
    brand         TEXT NOT NULL,
    fit           TEXT,
    unit_price    NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    unit_cost     NUMERIC(10, 2) NOT NULL CHECK (unit_cost >= 0),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    DATE NOT NULL
);
COMMENT ON TABLE products IS 'Every item the store sells. Sizes, colors and stock levels are in product_variants.';
COMMENT ON COLUMN products.product_type IS 'Books: Textbook, General Book. Clothing: T-Shirt, Hoodie, Jersey, Jacket, Sweatpants, Polo. Merchandise: Mug, Water Bottle, Cap, Beanie, Keychain, Sticker, Backpack, Lanyard, Blanket. Flags & Banners: Flag, Banner, Pennant, Car Flag, Garden Flag.';
COMMENT ON COLUMN products.brand IS 'Manufacturer or publisher, e.g. Nike, Champion, Under Armour, Colosseum, Pearson, IU Press.';
COMMENT ON COLUMN products.fit IS 'Clothing only: Men, Women, Youth or Unisex. NULL for non-clothing.';
COMMENT ON COLUMN products.unit_price IS 'Current list price in USD.';
COMMENT ON COLUMN products.unit_cost IS 'What the store pays the supplier per unit, in USD. Margin = unit_price - unit_cost.';
COMMENT ON COLUMN products.is_active IS 'FALSE for discontinued products.';

CREATE TABLE product_variants (
    variant_id      SERIAL PRIMARY KEY,
    product_id      INT NOT NULL REFERENCES products(product_id),
    size            TEXT,
    color           TEXT,
    stock_quantity  INT NOT NULL CHECK (stock_quantity >= 0),
    reorder_level   INT NOT NULL CHECK (reorder_level >= 0),
    UNIQUE (product_id, size, color)
);
COMMENT ON TABLE product_variants IS 'Sellable size/color combinations of a product with current inventory. Every product has at least one variant.';
COMMENT ON COLUMN product_variants.size IS 'Clothing: XS, S, M, L, XL, 2XL, 3XL (Youth: YS, YM, YL). Flags: 3x5 ft, 2x3 ft, 12x18 in. NULL when not applicable.';
COMMENT ON COLUMN product_variants.color IS 'e.g. Crimson, Cream, White, Black, Heather Gray. NULL when not applicable.';
COMMENT ON COLUMN product_variants.stock_quantity IS 'Units currently on hand.';
COMMENT ON COLUMN product_variants.reorder_level IS 'Restock is needed when stock_quantity <= reorder_level.';

CREATE TABLE books (
    product_id        INT PRIMARY KEY REFERENCES products(product_id),
    isbn              TEXT NOT NULL UNIQUE,
    author            TEXT NOT NULL,
    publisher         TEXT NOT NULL,
    edition           INT,
    format            TEXT NOT NULL,
    publication_year  INT NOT NULL
);
COMMENT ON TABLE books IS 'Extra details for products in the Books category. Title is products.name.';
COMMENT ON COLUMN books.format IS 'Hardcover, Paperback or Loose-leaf.';

CREATE TABLE courses (
    course_code  TEXT PRIMARY KEY,
    course_name  TEXT NOT NULL,
    school       TEXT NOT NULL
);
COMMENT ON TABLE courses IS 'IU Bloomington courses that have assigned textbooks.';
COMMENT ON COLUMN courses.course_code IS 'IU format, e.g. CSCI-C 211, BUS-K 201, MATH-M 211.';
COMMENT ON COLUMN courses.school IS 'e.g. Luddy School of Informatics, Computing, and Engineering; Kelley School of Business; College of Arts and Sciences.';

CREATE TABLE course_textbooks (
    course_code  TEXT NOT NULL REFERENCES courses(course_code),
    product_id   INT NOT NULL REFERENCES books(product_id),
    is_required  BOOLEAN NOT NULL,
    PRIMARY KEY (course_code, product_id)
);
COMMENT ON TABLE course_textbooks IS 'Which books are assigned to which courses.';

CREATE TABLE customers (
    customer_id    SERIAL PRIMARY KEY,
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    customer_type  TEXT NOT NULL,
    iu_school      TEXT,
    state          TEXT NOT NULL,
    joined_date    DATE NOT NULL
);
COMMENT ON COLUMN customers.customer_type IS 'Student, Faculty/Staff, Alumni or Visitor.';
COMMENT ON COLUMN customers.iu_school IS 'School a Student is enrolled in (same values as courses.school). NULL for other customer types.';
COMMENT ON COLUMN customers.state IS 'Two-letter US state code of the customer''s address, e.g. IN, IL, OH.';

CREATE TABLE promotions (
    promotion_id  SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    discount_pct  NUMERIC(5, 2) NOT NULL CHECK (discount_pct > 0 AND discount_pct < 100),
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL,
    category_id   INT REFERENCES categories(category_id)
);
COMMENT ON TABLE promotions IS 'Time-boxed sales events that repeat every academic year.';
COMMENT ON COLUMN promotions.name IS 'One of: Back to School, Homecoming Week, Black Friday, Holiday Gift Sale, Spring Textbook Rush, Little 500 Weekend, Graduation Celebration. Names do not include the year; filter on start_date for a specific year.';
COMMENT ON COLUMN promotions.category_id IS 'Category the discount applies to. NULL means store-wide.';

CREATE TABLE orders (
    order_id        SERIAL PRIMARY KEY,
    customer_id     INT NOT NULL REFERENCES customers(customer_id),
    order_date      TIMESTAMP NOT NULL,
    channel         TEXT NOT NULL,
    payment_method  TEXT NOT NULL,
    status          TEXT NOT NULL
);
COMMENT ON COLUMN orders.channel IS 'In-Store, Online or Game Day Kiosk (stands at Memorial Stadium and Assembly Hall on game days).';
COMMENT ON COLUMN orders.payment_method IS 'Credit Card, Debit Card, CrimsonCard (IU student ID card), Apple Pay or Cash.';
COMMENT ON COLUMN orders.status IS 'Completed or Refunded. Exclude Refunded orders when computing sales or revenue unless asked otherwise.';

CREATE TABLE order_items (
    order_item_id  SERIAL PRIMARY KEY,
    order_id       INT NOT NULL REFERENCES orders(order_id),
    variant_id     INT NOT NULL REFERENCES product_variants(variant_id),
    quantity       INT NOT NULL CHECK (quantity > 0),
    unit_price     NUMERIC(10, 2) NOT NULL,
    discount_pct   NUMERIC(5, 2) NOT NULL DEFAULT 0,
    promotion_id   INT REFERENCES promotions(promotion_id),
    line_total     NUMERIC(12, 2) GENERATED ALWAYS AS (ROUND(quantity * unit_price * (1 - discount_pct / 100), 2)) STORED
);
COMMENT ON TABLE order_items IS 'One row per product variant in an order. Join to product_variants then products for product details.';
COMMENT ON COLUMN order_items.unit_price IS 'List price per unit at the time of sale, before discount.';
COMMENT ON COLUMN order_items.discount_pct IS 'Percent discount applied to this line (0 when no promotion).';
COMMENT ON COLUMN order_items.line_total IS 'Revenue for this line after discount. Use SUM(line_total) for sales/revenue.';

CREATE INDEX ON products (category_id);
CREATE INDEX ON product_variants (product_id);
CREATE INDEX ON orders (customer_id);
CREATE INDEX ON orders (order_date);
CREATE INDEX ON order_items (order_id);
CREATE INDEX ON order_items (variant_id);
