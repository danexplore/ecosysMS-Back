"""
Queries SQL para tabelas Asaas.

Queries para operações CRUD nas tabelas:
- asaas_customers
- asaas_products
- asaas_payments
- asaas_subscriptions
"""

# ============================================================================
# CUSTOMERS QUERIES
# ============================================================================

INSERT_ASAAS_CUSTOMER = """
INSERT INTO asaas_customers (
    asaas_id, name, email, cpf_cnpj, phone, address, active, created_at, updated_at
) VALUES (
    %(asaas_id)s, %(name)s, %(email)s, %(cpf_cnpj)s, %(phone)s, 
    %(address)s::jsonb, %(active)s, NOW(), NOW()
)
ON CONFLICT (asaas_id) DO UPDATE SET
    name = EXCLUDED.name,
    email = EXCLUDED.email,
    phone = EXCLUDED.phone,
    address = EXCLUDED.address,
    active = EXCLUDED.active,
    updated_at = NOW()
RETURNING id, asaas_id, name, email, cpf_cnpj, phone, address, active, created_at, updated_at
"""

SELECT_ASAAS_CUSTOMER_BY_ID = """
SELECT id, asaas_id, name, email, cpf_cnpj, phone, address, active, created_at, updated_at
FROM asaas_customers
WHERE id = %(id)s
"""

SELECT_ASAAS_CUSTOMER_BY_ASAAS_ID = """
SELECT id, asaas_id, name, email, cpf_cnpj, phone, address, active, created_at, updated_at
FROM asaas_customers
WHERE asaas_id = %(asaas_id)s
"""

SELECT_ASAAS_CUSTOMER_BY_CPF_CNPJ = """
SELECT id, asaas_id, name, email, cpf_cnpj, phone, address, active, created_at, updated_at
FROM asaas_customers
WHERE cpf_cnpj = %(cpf_cnpj)s
"""

SELECT_ALL_ASAAS_CUSTOMERS = """
SELECT id, asaas_id, name, email, cpf_cnpj, phone, address, active, created_at, updated_at
FROM asaas_customers
WHERE (%(active)s IS NULL OR active = %(active)s)
ORDER BY created_at DESC
LIMIT %(limit)s OFFSET %(offset)s
"""

COUNT_ASAAS_CUSTOMERS = """
SELECT COUNT(*) as total
FROM asaas_customers
WHERE (%(active)s IS NULL OR active = %(active)s)
"""

UPDATE_ASAAS_CUSTOMER = """
UPDATE asaas_customers SET
    name = COALESCE(%(name)s, name),
    email = COALESCE(%(email)s, email),
    phone = COALESCE(%(phone)s, phone),
    address = COALESCE(%(address)s::jsonb, address),
    active = COALESCE(%(active)s, active),
    updated_at = NOW()
WHERE id = %(id)s
RETURNING id, asaas_id, name, email, cpf_cnpj, phone, address, active, created_at, updated_at
"""

DELETE_ASAAS_CUSTOMER = """
UPDATE asaas_customers SET active = false, updated_at = NOW()
WHERE id = %(id)s
RETURNING id
"""


# ============================================================================
# PRODUCTS QUERIES
# ============================================================================

INSERT_ASAAS_PRODUCT = """
INSERT INTO asaas_products (
    name, price, cycle, active, created_at
) VALUES (
    %(name)s, %(price)s, %(cycle)s, %(active)s, NOW()
)
RETURNING id, name, price, cycle, active, created_at
"""

SELECT_ASAAS_PRODUCT_BY_ID = """
SELECT id, name, price, cycle, active, created_at
FROM asaas_products
WHERE id = %(id)s
"""

SELECT_ALL_ASAAS_PRODUCTS = """
SELECT id, name, price, cycle, active, created_at
FROM asaas_products
WHERE (%(active)s IS NULL OR active = %(active)s)
ORDER BY created_at DESC
LIMIT %(limit)s OFFSET %(offset)s
"""

SELECT_ACTIVE_ASAAS_PRODUCTS = """
SELECT id, name, price, cycle, active, created_at
FROM asaas_products
WHERE active = true
ORDER BY name ASC
"""

COUNT_ASAAS_PRODUCTS = """
SELECT COUNT(*) as total
FROM asaas_products
WHERE (%(active)s IS NULL OR active = %(active)s)
"""

UPDATE_ASAAS_PRODUCT = """
UPDATE asaas_products SET
    name = COALESCE(%(name)s, name),
    price = COALESCE(%(price)s, price),
    cycle = COALESCE(%(cycle)s, cycle),
    active = COALESCE(%(active)s, active)
WHERE id = %(id)s
RETURNING id, name, price, cycle, active, created_at
"""

DELETE_ASAAS_PRODUCT = """
UPDATE asaas_products SET active = false
WHERE id = %(id)s
RETURNING id
"""


# ============================================================================
# PAYMENTS QUERIES
# ============================================================================

INSERT_ASAAS_PAYMENT = """
INSERT INTO asaas_payments (
    asaas_id, cliente_id, value, status, due_date, payment_date, 
    invoice_url, billing_type, description, created_at
) VALUES (
    %(asaas_id)s, %(cliente_id)s, %(value)s, %(status)s, %(due_date)s, 
    %(payment_date)s, %(invoice_url)s, %(billing_type)s, %(description)s, NOW()
)
ON CONFLICT (asaas_id) DO UPDATE SET
    status = EXCLUDED.status,
    payment_date = EXCLUDED.payment_date,
    invoice_url = EXCLUDED.invoice_url
RETURNING id, asaas_id, cliente_id, value, status, due_date, payment_date, invoice_url, billing_type, description, created_at
"""

SELECT_ASAAS_PAYMENT_BY_ID = """
SELECT id, asaas_id, cliente_id, value, status, due_date, payment_date, 
       invoice_url, billing_type, description, created_at
FROM asaas_payments
WHERE id = %(id)s
"""

SELECT_ASAAS_PAYMENT_BY_ASAAS_ID = """
SELECT id, asaas_id, cliente_id, value, status, due_date, payment_date, 
       invoice_url, billing_type, description, created_at
FROM asaas_payments
WHERE asaas_id = %(asaas_id)s
"""

SELECT_ALL_ASAAS_PAYMENTS = """
SELECT id, asaas_id, cliente_id, value, status, due_date, payment_date, 
       invoice_url, billing_type, description, created_at
FROM asaas_payments
WHERE (%(status)s IS NULL OR status = %(status)s)
  AND (%(cliente_id)s IS NULL OR cliente_id = %(cliente_id)s)
ORDER BY created_at DESC
LIMIT %(limit)s OFFSET %(offset)s
"""

SELECT_PAYMENTS_BY_CUSTOMER = """
SELECT id, asaas_id, cliente_id, value, status, due_date, payment_date, 
       invoice_url, billing_type, description, created_at
FROM asaas_payments
WHERE cliente_id = %(cliente_id)s
ORDER BY created_at DESC
LIMIT %(limit)s OFFSET %(offset)s
"""

COUNT_ASAAS_PAYMENTS = """
SELECT COUNT(*) as total
FROM asaas_payments
WHERE (%(status)s IS NULL OR status = %(status)s)
  AND (%(cliente_id)s IS NULL OR cliente_id = %(cliente_id)s)
"""

UPDATE_ASAAS_PAYMENT_STATUS = """
UPDATE asaas_payments SET
    status = %(status)s,
    payment_date = %(payment_date)s
WHERE asaas_id = %(asaas_id)s
RETURNING id, asaas_id, cliente_id, value, status, due_date, payment_date, invoice_url, billing_type, description, created_at
"""

DELETE_ASAAS_PAYMENT = """
DELETE FROM asaas_payments
WHERE id = %(id)s
RETURNING id
"""


# ============================================================================
# SUBSCRIPTIONS QUERIES
# ============================================================================

INSERT_ASAAS_SUBSCRIPTION = """
INSERT INTO asaas_subscriptions (
    asaas_id, cliente_id, product_id, value, cycle, status, 
    next_due_date, billing_type, description, created_at
) VALUES (
    %(asaas_id)s, %(cliente_id)s, %(product_id)s, %(value)s, %(cycle)s, 
    %(status)s, %(next_due_date)s, %(billing_type)s, %(description)s, NOW()
)
ON CONFLICT (asaas_id) DO UPDATE SET
    status = EXCLUDED.status,
    next_due_date = EXCLUDED.next_due_date,
    value = EXCLUDED.value
RETURNING id, asaas_id, cliente_id, product_id, value, cycle, status, next_due_date, billing_type, description, created_at
"""

SELECT_ASAAS_SUBSCRIPTION_BY_ID = """
SELECT id, asaas_id, cliente_id, product_id, value, cycle, status, 
       next_due_date, billing_type, description, created_at
FROM asaas_subscriptions
WHERE id = %(id)s
"""

SELECT_ASAAS_SUBSCRIPTION_BY_ASAAS_ID = """
SELECT id, asaas_id, cliente_id, product_id, value, cycle, status, 
       next_due_date, billing_type, description, created_at
FROM asaas_subscriptions
WHERE asaas_id = %(asaas_id)s
"""

SELECT_ALL_ASAAS_SUBSCRIPTIONS = """
SELECT id, asaas_id, cliente_id, product_id, value, cycle, status, 
       next_due_date, billing_type, description, created_at
FROM asaas_subscriptions
WHERE (%(status)s IS NULL OR status = %(status)s)
  AND (%(cliente_id)s IS NULL OR cliente_id = %(cliente_id)s)
ORDER BY created_at DESC
LIMIT %(limit)s OFFSET %(offset)s
"""

SELECT_SUBSCRIPTIONS_BY_CUSTOMER = """
SELECT id, asaas_id, cliente_id, product_id, value, cycle, status, 
       next_due_date, billing_type, description, created_at
FROM asaas_subscriptions
WHERE cliente_id = %(cliente_id)s
ORDER BY created_at DESC
"""

SELECT_ACTIVE_SUBSCRIPTIONS = """
SELECT id, asaas_id, cliente_id, product_id, value, cycle, status, 
       next_due_date, billing_type, description, created_at
FROM asaas_subscriptions
WHERE status = 'ACTIVE'
ORDER BY created_at DESC
"""

COUNT_ASAAS_SUBSCRIPTIONS = """
SELECT COUNT(*) as total
FROM asaas_subscriptions
WHERE (%(status)s IS NULL OR status = %(status)s)
  AND (%(cliente_id)s IS NULL OR cliente_id = %(cliente_id)s)
"""

UPDATE_ASAAS_SUBSCRIPTION = """
UPDATE asaas_subscriptions SET
    status = COALESCE(%(status)s, status),
    value = COALESCE(%(value)s, value),
    cycle = COALESCE(%(cycle)s, cycle),
    next_due_date = COALESCE(%(next_due_date)s, next_due_date),
    billing_type = COALESCE(%(billing_type)s, billing_type),
    description = COALESCE(%(description)s, description)
WHERE id = %(id)s
RETURNING id, asaas_id, cliente_id, product_id, value, cycle, status, next_due_date, billing_type, description, created_at
"""

DELETE_ASAAS_SUBSCRIPTION = """
UPDATE asaas_subscriptions SET status = 'INACTIVE'
WHERE id = %(id)s
RETURNING id
"""


# ============================================================================
# DASHBOARD / METRICS QUERIES
# ============================================================================

SELECT_MRR = """
SELECT COALESCE(SUM(value), 0) as mrr
FROM asaas_subscriptions
WHERE status = 'ACTIVE'
  AND cycle = 'MONTHLY'
"""

SELECT_PAYMENT_STATS = """
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'PENDING') as pending,
    COUNT(*) FILTER (WHERE status = 'RECEIVED') as received,
    COUNT(*) FILTER (WHERE status = 'OVERDUE') as overdue,
    COUNT(*) FILTER (WHERE status = 'REFUNDED') as refunded,
    COALESCE(SUM(value), 0) as total_value,
    COALESCE(SUM(value) FILTER (WHERE status = 'RECEIVED'), 0) as received_value,
    COALESCE(SUM(value) FILTER (WHERE status = 'PENDING'), 0) as pending_value
FROM asaas_payments
WHERE (%(start_date)s IS NULL OR created_at >= %(start_date)s)
  AND (%(end_date)s IS NULL OR created_at <= %(end_date)s)
"""

SELECT_OVERDUE_CUSTOMERS = """
SELECT DISTINCT c.id, c.asaas_id, c.name, c.email, c.cpf_cnpj,
       COUNT(p.id) as overdue_count,
       SUM(p.value) as overdue_value
FROM asaas_customers c
INNER JOIN asaas_payments p ON c.id = p.cliente_id
WHERE p.status = 'OVERDUE'
GROUP BY c.id, c.asaas_id, c.name, c.email, c.cpf_cnpj
ORDER BY overdue_value DESC
LIMIT %(limit)s OFFSET %(offset)s
"""

SELECT_REVENUE_BY_PERIOD = """
SELECT 
    DATE_TRUNC('month', payment_date) as month,
    COUNT(*) as payment_count,
    SUM(value) as total_value
FROM asaas_payments
WHERE status = 'RECEIVED'
  AND payment_date >= %(start_date)s
  AND payment_date <= %(end_date)s
GROUP BY DATE_TRUNC('month', payment_date)
ORDER BY month DESC
"""

SELECT_SUBSCRIPTION_METRICS = """
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'ACTIVE') as active,
    COUNT(*) FILTER (WHERE status = 'INACTIVE') as inactive,
    COUNT(*) FILTER (WHERE status = 'EXPIRED') as expired,
    COALESCE(SUM(value) FILTER (WHERE status = 'ACTIVE' AND cycle = 'MONTHLY'), 0) as mrr
FROM asaas_subscriptions
"""


# ============================================================================
# CUSTOMER STATS QUERIES
# ============================================================================

SELECT_CUSTOMER_STATS = """
SELECT 
    COUNT(*) as total_customers,
    COUNT(*) FILTER (WHERE active = true) as active_customers,
    COUNT(*) FILTER (WHERE active = false) as inactive_customers,
    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') as new_last_30_days,
    (
        SELECT COUNT(DISTINCT c.id)
        FROM asaas_customers c
        INNER JOIN asaas_payments p ON c.id = p.cliente_id
        WHERE p.status = 'OVERDUE'
    ) as overdue_customers
FROM asaas_customers
"""


# ============================================================================
# CHURN QUERIES
# ============================================================================

SELECT_CHURN_RATE = """
WITH monthly_stats AS (
    SELECT 
        DATE_TRUNC('month', created_at) as month,
        COUNT(*) as new_subscriptions
    FROM asaas_subscriptions
    WHERE created_at >= %(start_date)s
      AND created_at <= %(end_date)s
    GROUP BY DATE_TRUNC('month', created_at)
),
churned AS (
    SELECT 
        DATE_TRUNC('month', created_at) as month,
        COUNT(*) as churned_subscriptions
    FROM asaas_subscriptions
    WHERE status IN ('INACTIVE', 'EXPIRED')
      AND created_at >= %(start_date)s
      AND created_at <= %(end_date)s
    GROUP BY DATE_TRUNC('month', created_at)
)
SELECT 
    COALESCE(m.month, c.month) as month,
    COALESCE(m.new_subscriptions, 0) as new_subscriptions,
    COALESCE(c.churned_subscriptions, 0) as churned,
    CASE 
        WHEN COALESCE(m.new_subscriptions, 0) > 0 
        THEN ROUND((COALESCE(c.churned_subscriptions, 0)::numeric / m.new_subscriptions) * 100, 2)
        ELSE 0
    END as churn_rate
FROM monthly_stats m
FULL OUTER JOIN churned c ON m.month = c.month
ORDER BY month DESC
"""

SELECT_OVERALL_CHURN = """
SELECT 
    COUNT(*) FILTER (WHERE status = 'ACTIVE') as active,
    COUNT(*) FILTER (WHERE status IN ('INACTIVE', 'EXPIRED')) as churned,
    COUNT(*) as total,
    CASE 
        WHEN COUNT(*) > 0 
        THEN ROUND((COUNT(*) FILTER (WHERE status IN ('INACTIVE', 'EXPIRED'))::numeric / COUNT(*)) * 100, 2)
        ELSE 0
    END as churn_rate
FROM asaas_subscriptions
"""


# ============================================================================
# SYNC QUERIES
# ============================================================================

INSERT_OR_UPDATE_ASAAS_PAYMENT = """
INSERT INTO asaas_payments (
    asaas_id, cliente_id, value, status, due_date, payment_date, 
    invoice_url, billing_type, description, created_at
) VALUES (
    %(asaas_id)s, %(cliente_id)s, %(value)s, %(status)s, %(due_date)s, 
    %(payment_date)s, %(invoice_url)s, %(billing_type)s, %(description)s, NOW()
)
ON CONFLICT (asaas_id) DO UPDATE SET
    status = EXCLUDED.status,
    payment_date = EXCLUDED.payment_date,
    invoice_url = EXCLUDED.invoice_url
RETURNING id
"""

INSERT_OR_UPDATE_ASAAS_SUBSCRIPTION = """
INSERT INTO asaas_subscriptions (
    asaas_id, cliente_id, product_id, value, cycle, status, 
    next_due_date, billing_type, description, created_at
) VALUES (
    %(asaas_id)s, %(cliente_id)s, %(product_id)s, %(value)s, %(cycle)s, 
    %(status)s, %(next_due_date)s, %(billing_type)s, %(description)s, NOW()
)
ON CONFLICT (asaas_id) DO UPDATE SET
    status = EXCLUDED.status,
    next_due_date = EXCLUDED.next_due_date,
    value = EXCLUDED.value,
    cycle = EXCLUDED.cycle
RETURNING id
"""
