-- ============================================================================
-- SCRIPT PARA REMOVER TABELAS DO SISTEMA DE PAGAMENTOS ASAAS
-- Execute este script no banco de dados para remover todas as tabelas
-- ============================================================================

-- Desabilitar verificação de foreign keys temporariamente
SET session_replication_role = 'replica';

-- Remover tabelas de pagamentos/assinaturas primeiro (dependências)
DROP TABLE IF EXISTS asaas_webhook_events CASCADE;
DROP TABLE IF EXISTS asaas_payments CASCADE;
DROP TABLE IF EXISTS asaas_subscriptions CASCADE;
DROP TABLE IF EXISTS asaas_products CASCADE;
DROP TABLE IF EXISTS asaas_customers CASCADE;

-- Remover índices (se existirem separadamente)
DROP INDEX IF EXISTS idx_asaas_customers_cpf_cnpj;
DROP INDEX IF EXISTS idx_asaas_customers_asaas_id;
DROP INDEX IF EXISTS idx_asaas_customers_email;
DROP INDEX IF EXISTS idx_asaas_payments_customer;
DROP INDEX IF EXISTS idx_asaas_payments_status;
DROP INDEX IF EXISTS idx_asaas_payments_due_date;
DROP INDEX IF EXISTS idx_asaas_payments_asaas_id;
DROP INDEX IF EXISTS idx_asaas_subscriptions_customer;
DROP INDEX IF EXISTS idx_asaas_subscriptions_status;
DROP INDEX IF EXISTS idx_asaas_subscriptions_asaas_id;
DROP INDEX IF EXISTS idx_asaas_products_active;
DROP INDEX IF EXISTS idx_asaas_webhook_events_payment;
DROP INDEX IF EXISTS idx_asaas_webhook_events_subscription;

-- Remover tipos enum (se existirem)
DROP TYPE IF EXISTS payment_status CASCADE;
DROP TYPE IF EXISTS billing_type CASCADE;
DROP TYPE IF EXISTS subscription_cycle CASCADE;
DROP TYPE IF EXISTS subscription_status CASCADE;

-- Reabilitar verificação de foreign keys
SET session_replication_role = 'origin';

-- Verificar se todas as tabelas foram removidas
DO $$
DECLARE
    table_exists boolean;
BEGIN
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'asaas_%'
    ) INTO table_exists;
    
    IF table_exists THEN
        RAISE NOTICE '⚠️ Ainda existem tabelas Asaas. Execute o script novamente.';
    ELSE
        RAISE NOTICE '✅ Todas as tabelas Asaas foram removidas com sucesso!';
    END IF;
END $$;
