from scripts.synthetic_data import COLUMNS, generate


def test_generation_is_deterministic():
    a, b = generate(seed=7), generate(seed=7)
    assert a.orders[:50] == b.orders[:50]
    assert a.order_items[-50:] == b.order_items[-50:]


def test_rows_match_columns_and_foreign_keys_resolve():
    data = generate()
    for table, cols in COLUMNS.items():
        rows = getattr(data, table)
        assert rows, table
        assert all(len(r) == len(cols) for r in rows), table

    product_ids = {p[0] for p in data.products}
    variant_ids = {v[0] for v in data.product_variants}
    customer_ids = {c[0] for c in data.customers}
    order_ids = {o[0] for o in data.orders}
    course_codes = {c[0] for c in data.courses}
    book_ids = {b[0] for b in data.books}

    assert {v[1] for v in data.product_variants} <= product_ids
    assert book_ids <= product_ids
    assert {ct[0] for ct in data.course_textbooks} <= course_codes
    assert {ct[1] for ct in data.course_textbooks} <= book_ids
    assert {o[1] for o in data.orders} <= customer_ids
    assert {i[1] for i in data.order_items} <= order_ids
    assert {i[2] for i in data.order_items} <= variant_ids


def test_customers_have_joined_before_ordering():
    data = generate()
    joined = {c[0]: c[7] for c in data.customers}
    assert all(joined[o[1]] <= o[2].date() for o in data.orders)
