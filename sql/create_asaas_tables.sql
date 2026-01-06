-- ============================================================================
-- TABELAS ASAAS - ecosys Payments API
-- 
-- Execute estas queries no Supabase Dashboard > SQL Editor
-- ============================================================================

-- ============================================================================
-- 1. TABELA: asaas_customers
-- Armazena clientes sincronizados com Asaas
-- ============================================================================

CREATE TABLE IF NOT EXISTS asaas_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asaas_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    cpf_cnpj VARCHAR(20) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address JSONB DEFAULT '{}',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_asaas_customers_asaas_id ON asaas_customers(asaas_id);
CREATE INDEX IF NOT EXISTS idx_asaas_customers_cpf_cnpj ON asaas_customers(cpf_cnpj);
CREATE INDEX IF NOT EXISTS idx_asaas_customers_email ON asaas_customers(email);
CREATE INDEX IF NOT EXISTS idx_asaas_customers_active ON asaas_customers(active);

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_asaas_customers_updated_at
    BEFORE UPDATE ON asaas_customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 2. TABELA: asaas_products
-- Produtos/Planos disponíveis para cobrança
-- ============================================================================

CREATE TABLE IF NOT EXISTS asaas_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    cycle VARCHAR(20) DEFAULT 'MONTHLY' CHECK (cycle IN ('WEEKLY', 'BIWEEKLY', 'MONTHLY', 'QUARTERLY', 'SEMIANNUALLY', 'YEARLY')),
    description TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_asaas_products_active ON asaas_products(active);
CREATE INDEX IF NOT EXISTS idx_asaas_products_cycle ON asaas_products(cycle);


-- ============================================================================
-- 3. TABELA: asaas_payments
-- Cobranças/Pagamentos sincronizados com Asaas
-- ============================================================================

CREATE TABLE IF NOT EXISTS asaas_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asaas_id VARCHAR(50) UNIQUE NOT NULL,
    cliente_id UUID REFERENCES asaas_customers(id),
    value DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN (
        'PENDING', 'RECEIVED', 'CONFIRMED', 'OVERDUE', 'REFUNDED',
        'RECEIVED_IN_CASH', 'REFUND_REQUESTED', 'CHARGEBACK_REQUESTED',
        'CHARGEBACK_DISPUTE', 'AWAITING_CHARGEBACK_REVERSAL',
        'DUNNING_REQUESTED', 'DUNNING_RECEIVED', 'AWAITING_RISK_ANALYSIS'
    )),
    billing_type VARCHAR(20) DEFAULT 'UNDEFINED' CHECK (billing_type IN ('BOLETO', 'CREDIT_CARD', 'PIX', 'UNDEFINED')),
    due_date DATE NOT NULL,
    payment_date TIMESTAMP WITH TIME ZONE,
    invoice_url TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_asaas_payments_asaas_id ON asaas_payments(asaas_id);
CREATE INDEX IF NOT EXISTS idx_asaas_payments_cliente_id ON asaas_payments(cliente_id);
CREATE INDEX IF NOT EXISTS idx_asaas_payments_status ON asaas_payments(status);
CREATE INDEX IF NOT EXISTS idx_asaas_payments_due_date ON asaas_payments(due_date);
CREATE INDEX IF NOT EXISTS idx_asaas_payments_created_at ON asaas_payments(created_at);


-- ============================================================================
-- 4. TABELA: asaas_subscriptions
-- Assinaturas recorrentes
-- ============================================================================

CREATE TABLE IF NOT EXISTS asaas_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asaas_id VARCHAR(50) UNIQUE NOT NULL,
    cliente_id UUID REFERENCES asaas_customers(id),
    product_id UUID REFERENCES asaas_products(id),
    value DECIMAL(10,2) NOT NULL,
    cycle VARCHAR(20) DEFAULT 'MONTHLY' CHECK (cycle IN ('WEEKLY', 'BIWEEKLY', 'MONTHLY', 'QUARTERLY', 'SEMIANNUALLY', 'YEARLY')),
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'EXPIRED')),
    billing_type VARCHAR(20) DEFAULT 'UNDEFINED' CHECK (billing_type IN ('BOLETO', 'CREDIT_CARD', 'PIX', 'UNDEFINED')),
    next_due_date DATE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_asaas_subscriptions_asaas_id ON asaas_subscriptions(asaas_id);
CREATE INDEX IF NOT EXISTS idx_asaas_subscriptions_cliente_id ON asaas_subscriptions(cliente_id);
CREATE INDEX IF NOT EXISTS idx_asaas_subscriptions_product_id ON asaas_subscriptions(product_id);
CREATE INDEX IF NOT EXISTS idx_asaas_subscriptions_status ON asaas_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_asaas_subscriptions_next_due_date ON asaas_subscriptions(next_due_date);


-- ============================================================================
-- VIEWS ÚTEIS
-- ============================================================================

-- View: MRR (Monthly Recurring Revenue)
CREATE OR REPLACE VIEW view_mrr AS
SELECT 
    SUM(value) as mrr,
    COUNT(*) as active_subscriptions
FROM asaas_subscriptions
WHERE status = 'ACTIVE' AND cycle = 'MONTHLY';


-- View: Resumo de pagamentos por status
CREATE OR REPLACE VIEW view_payment_summary AS
SELECT 
    status,
    COUNT(*) as count,
    SUM(value) as total_value
FROM asaas_payments
GROUP BY status;


-- View: Clientes inadimplentes
CREATE OR REPLACE VIEW view_overdue_customers AS
SELECT 
    c.id,
    c.asaas_id,
    c.name,
    c.email,
    c.cpf_cnpj,
    COUNT(p.id) as overdue_count,
    SUM(p.value) as overdue_value
FROM asaas_customers c
INNER JOIN asaas_payments p ON c.id = p.cliente_id
WHERE p.status = 'OVERDUE'
GROUP BY c.id, c.asaas_id, c.name, c.email, c.cpf_cnpj
ORDER BY overdue_value DESC;


-- ============================================================================
-- ROW LEVEL SECURITY (RLS) - Opcional
-- Descomente se necessário controle de acesso por tenant
-- ============================================================================

-- ALTER TABLE asaas_customers ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE asaas_products ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE asaas_payments ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE asaas_subscriptions ENABLE ROW LEVEL SECURITY;


-- ============================================================================
-- COMENTÁRIOS NAS TABELAS
-- ============================================================================

COMMENT ON TABLE asaas_customers IS 'Clientes sincronizados com gateway Asaas';
COMMENT ON TABLE asaas_products IS 'Produtos e planos disponíveis para cobrança';
COMMENT ON TABLE asaas_payments IS 'Cobranças e pagamentos do Asaas';
COMMENT ON TABLE asaas_subscriptions IS 'Assinaturas recorrentes';

COMMENT ON COLUMN asaas_customers.asaas_id IS 'ID único do cliente no Asaas';
COMMENT ON COLUMN asaas_payments.asaas_id IS 'ID único do pagamento no Asaas';
COMMENT ON COLUMN asaas_subscriptions.asaas_id IS 'ID único da assinatura no Asaas';
