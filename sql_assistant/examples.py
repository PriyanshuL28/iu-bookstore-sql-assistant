"""Curated question -> SQL pairs used as dynamic few-shot examples.

Keep these distinct from eval/questions.json so the evaluation measures generalization.
"""

FEW_SHOT_EXAMPLES = [
    {
        "question": "How many crimson hoodies in size L do we have in stock?",
        "sql": """SELECT SUM(v.stock_quantity) AS units_in_stock
FROM product_variants v
JOIN products p ON p.product_id = v.product_id
WHERE p.product_type = 'Hoodie' AND v.color = 'Crimson' AND v.size = 'L'""",
    },
    {
        "question": "What was the total clothing revenue in 2025?",
        "sql": """SELECT ROUND(SUM(oi.line_total), 2) AS clothing_revenue
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN product_variants v ON v.variant_id = oi.variant_id
JOIN products p ON p.product_id = v.product_id
JOIN categories c ON c.category_id = p.category_id
WHERE c.name = 'Clothing'
  AND o.status = 'Completed'
  AND o.order_date >= '2025-01-01' AND o.order_date < '2026-01-01'""",
    },
    {
        "question": "What are the top 5 best-selling products by units sold?",
        "sql": """SELECT p.name, p.product_type, SUM(oi.quantity) AS units_sold
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN product_variants v ON v.variant_id = oi.variant_id
JOIN products p ON p.product_id = v.product_id
WHERE o.status = 'Completed'
GROUP BY p.product_id, p.name, p.product_type
ORDER BY units_sold DESC
LIMIT 5""",
    },
    {
        "question": "Which required textbooks are assigned to CSCI-C 211 and how much do they cost?",
        "sql": """SELECT p.name AS title, b.author, b.isbn, p.unit_price
FROM course_textbooks ct
JOIN books b ON b.product_id = ct.product_id
JOIN products p ON p.product_id = b.product_id
WHERE ct.course_code = 'CSCI-C 211' AND ct.is_required""",
    },
    {
        "question": "Which products need to be restocked?",
        "sql": """SELECT p.name, v.size, v.color, v.stock_quantity, v.reorder_level
FROM product_variants v
JOIN products p ON p.product_id = v.product_id
WHERE p.is_active AND v.stock_quantity <= v.reorder_level
ORDER BY v.stock_quantity, p.name
LIMIT 50""",
    },
    {
        "question": "Show monthly revenue for 2025.",
        "sql": """SELECT DATE_TRUNC('month', o.order_date)::date AS month, ROUND(SUM(oi.line_total), 2) AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.status = 'Completed'
  AND o.order_date >= '2025-01-01' AND o.order_date < '2026-01-01'
GROUP BY 1
ORDER BY 1""",
    },
    {
        "question": "How much money did customers save during Black Friday 2025?",
        "sql": """SELECT ROUND(SUM(oi.quantity * oi.unit_price - oi.line_total), 2) AS total_discount_given
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN promotions pr ON pr.promotion_id = oi.promotion_id
WHERE pr.name = 'Black Friday' AND EXTRACT(YEAR FROM pr.start_date) = 2025
  AND o.status = 'Completed'""",
    },
    {
        "question": "What percentage of in-store student orders were paid with CrimsonCard?",
        "sql": """SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE o.payment_method = 'CrimsonCard') / COUNT(*), 2) AS crimsoncard_pct
FROM orders o
JOIN customers cu ON cu.customer_id = o.customer_id
WHERE cu.customer_type = 'Student' AND o.channel = 'In-Store'""",
    },
    {
        "question": "What is the average order value for each sales channel?",
        "sql": """WITH order_totals AS (
    SELECT o.order_id, o.channel, SUM(oi.line_total) AS order_total
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status = 'Completed'
    GROUP BY o.order_id, o.channel
)
SELECT channel, ROUND(AVG(order_total), 2) AS avg_order_value, COUNT(*) AS orders
FROM order_totals
GROUP BY channel
ORDER BY avg_order_value DESC""",
    },
    {
        "question": "Which clothing brand made the most gross profit?",
        "sql": """SELECT p.brand, ROUND(SUM(oi.line_total - oi.quantity * p.unit_cost), 2) AS gross_profit
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN product_variants v ON v.variant_id = oi.variant_id
JOIN products p ON p.product_id = v.product_id
JOIN categories c ON c.category_id = p.category_id
WHERE c.name = 'Clothing' AND o.status = 'Completed'
GROUP BY p.brand
ORDER BY gross_profit DESC
LIMIT 1""",
    },
    {
        "question": "Who are our top 10 customers by total spending?",
        "sql": """SELECT cu.first_name, cu.last_name, cu.customer_type, ROUND(SUM(oi.line_total), 2) AS total_spent
FROM customers cu
JOIN orders o ON o.customer_id = cu.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.status = 'Completed'
GROUP BY cu.customer_id, cu.first_name, cu.last_name, cu.customer_type
ORDER BY total_spent DESC
LIMIT 10""",
    },
    {
        "question": "How many textbooks did Kelley School of Business students buy?",
        "sql": """SELECT SUM(oi.quantity) AS textbooks_bought
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN customers cu ON cu.customer_id = o.customer_id
JOIN product_variants v ON v.variant_id = oi.variant_id
JOIN products p ON p.product_id = v.product_id
WHERE p.product_type = 'Textbook'
  AND cu.customer_type = 'Student'
  AND cu.iu_school = 'Kelley School of Business'
  AND o.status = 'Completed'""",
    },
    {
        "question": "If we sold all remaining jersey inventory at list price, how much revenue would that be?",
        "sql": """SELECT ROUND(SUM(v.stock_quantity * p.unit_price), 2) AS potential_revenue
FROM product_variants v
JOIN products p ON p.product_id = v.product_id
WHERE p.product_type = 'Jersey' AND p.is_active""",
    },
    {
        "question": "How many Nike hoodies are left in stock and how many have we sold?",
        "sql": """WITH stock AS (
    SELECT SUM(v.stock_quantity) AS units_in_stock
    FROM product_variants v
    JOIN products p ON p.product_id = v.product_id
    WHERE p.product_type = 'Hoodie' AND p.brand = 'Nike'
),
sold AS (
    SELECT SUM(oi.quantity) AS units_sold
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    JOIN product_variants v ON v.variant_id = oi.variant_id
    JOIN products p ON p.product_id = v.product_id
    WHERE p.product_type = 'Hoodie' AND p.brand = 'Nike' AND o.status = 'Completed'
)
SELECT stock.units_in_stock, sold.units_sold
FROM stock CROSS JOIN sold""",
    },
    {
        "question": "How much did the Game Day Kiosks sell on each home game day in fall 2025?",
        "sql": """SELECT o.order_date::date AS game_day, COUNT(DISTINCT o.order_id) AS orders, ROUND(SUM(oi.line_total), 2) AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.channel = 'Game Day Kiosk' AND o.status = 'Completed'
  AND o.order_date >= '2025-08-01' AND o.order_date < '2026-01-01'
GROUP BY 1
ORDER BY 1""",
    },
]
