# ============================================================================
# QUERIES DE CLIENTES
# ============================================================================

SELECT_CLIENTES = """
select
  *
from clientes_atual
order by data_adesao desc
"""

SELECT_CLIENTES_COMISSAO = """
-- Query para buscar todos os clientes para cálculo de comissão
-- Considera apenas clientes com valor > 0
-- meses_ativo: calculado como meses de COMISSÃO + 1 (para garantir 1ª comissão paga)
-- Exemplo: adesão nov/2025, atual dez/2025 → meses_ativo = 2 (garante 1ª comissão)
SELECT
    client_id,
    nome,
    vendedor,
    valor,
    taxa_setup,
    status,
    status_financeiro,
    parcelas_atrasadas,
    data_adesao,
    data_cancelamento,
    pipeline,
    -- Calcular meses de comissão + 1 para garantir primeira comissão
    GREATEST(
        1,
        (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM CURRENT_DATE) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo
FROM clientes_atual
WHERE valor > 0
ORDER BY data_adesao DESC
"""

SELECT_CLIENTES_COMISSAO_BY_MONTH = """
-- Query para buscar clientes para cálculo de comissão ATÉ um mês específico
-- Considera apenas clientes com valor > 0
-- Parâmetro: mês no formato YYYY-MM (filtra clientes que aderiram até o final deste mês)
-- meses_ativo: calculado como meses de COMISSÃO + 1 até HOJE
-- meses_ativo_referencia: calculado até o mês de referência + 1
SELECT
    client_id,
    nome,
    vendedor,
    valor,
    taxa_setup,
    status,
    status_financeiro,
    parcelas_atrasadas,
    data_adesao,
    data_cancelamento,
    pipeline,
    -- Calcular meses de comissão até HOJE + 1
    GREATEST(
        1,
        (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM CURRENT_DATE) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo,
    -- Calcular meses de comissão até o mês de referência + 1
    GREATEST(
        1,
        (EXTRACT(YEAR FROM TO_DATE(%s, 'YYYY-MM')) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM TO_DATE(%s, 'YYYY-MM')) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo_referencia
FROM clientes_atual
WHERE valor > 0
  AND data_adesao <= (TO_DATE(%s, 'YYYY-MM') + INTERVAL '1 month - 1 day')::date
ORDER BY data_adesao DESC
"""

SELECT_CLIENTES_INADIMPLENTES = """
-- Query para buscar clientes inadimplentes
-- Considera apenas clientes com valor > 0
SELECT
    client_id,
    nome,
    vendedor,
    valor,
    taxa_setup,
    status,
    status_financeiro,
    parcelas_atrasadas,
    data_adesao,
    data_cancelamento,
    pipeline,
    -- Calcular meses de vigência até HOJE
    GREATEST(
        1,
        (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM CURRENT_DATE) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo
FROM clientes_atual
WHERE status_financeiro = 'inadimplente'
  AND valor > 0
ORDER BY data_adesao DESC
"""

SELECT_CLIENTES_INADIMPLENTES_BY_MONTH = """
-- Query para buscar clientes inadimplentes ATÉ um mês específico
-- Considera apenas clientes com valor > 0
-- Parâmetro: mês no formato YYYY-MM (filtra clientes que aderiram até o final deste mês)
SELECT
    client_id,
    nome,
    vendedor,
    valor,
    taxa_setup,
    status,
    status_financeiro,
    parcelas_atrasadas,
    data_adesao,
    data_cancelamento,
    pipeline,
    -- Calcular meses de vigência até HOJE
    GREATEST(
        1,
        (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM CURRENT_DATE) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo,
    -- Calcular meses de vigência até o mês de referência
    GREATEST(
        1,
        (EXTRACT(YEAR FROM TO_DATE(%s, 'YYYY-MM')) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM TO_DATE(%s, 'YYYY-MM')) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo_referencia
FROM clientes_atual
WHERE status_financeiro = 'inadimplente'
  AND valor > 0
  AND data_adesao <= (TO_DATE(%s, 'YYYY-MM') + INTERVAL '1 month - 1 day')::date
ORDER BY data_adesao DESC
"""

SELECT_NOVOS_CLIENTES_MES = """
-- Query para buscar novos clientes do mês atual
-- Considera apenas clientes com valor > 0
SELECT
    client_id,
    nome,
    vendedor,
    valor,
    taxa_setup,
    status,
    status_financeiro,
    parcelas_atrasadas,
    data_adesao,
    data_cancelamento,
    pipeline,
    -- Calcular meses de vigência até HOJE
    GREATEST(
        1,
        (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM CURRENT_DATE) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo
FROM clientes_atual
WHERE data_adesao >= %s
  AND valor > 0
ORDER BY data_adesao DESC
"""

SELECT_NOVOS_CLIENTES_BY_MONTH = """
-- Query para buscar novos clientes ATÉ um mês específico
-- Considera apenas clientes com valor > 0
-- Parâmetro: mês no formato YYYY-MM (filtra clientes que aderiram até o final deste mês)
SELECT
    client_id,
    nome,
    vendedor,
    valor,
    taxa_setup,
    status,
    status_financeiro,
    parcelas_atrasadas,
    data_adesao,
    data_cancelamento,
    pipeline,
    -- Calcular meses de vigência até HOJE
    GREATEST(
        1,
        (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM CURRENT_DATE) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo,
    -- Calcular meses de vigência até o mês de referência
    GREATEST(
        1,
        (EXTRACT(YEAR FROM TO_DATE(%s, 'YYYY-MM')) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM TO_DATE(%s, 'YYYY-MM')) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo_referencia
FROM clientes_atual
WHERE data_adesao <= (TO_DATE(%s, 'YYYY-MM') + INTERVAL '1 month - 1 day')::date
  AND valor > 0
ORDER BY data_adesao DESC
"""

SELECT_VENDAS_DO_MES = """
-- Query para buscar vendas (novos clientes) de um mês específico
-- Para cálculo de gamificação (tier bronze/prata/ouro)
-- Parâmetro: mês no formato YYYY-MM (filtra clientes que aderiram NAQUELE mês específico)
SELECT
    client_id,
    nome,
    vendedor,
    valor,
    taxa_setup,
    status,
    status_financeiro,
    parcelas_atrasadas,
    data_adesao,
    data_cancelamento,
    pipeline,
    -- Calcular meses de vigência até HOJE
    GREATEST(
        1,
        (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM CURRENT_DATE) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo
FROM clientes_atual
WHERE TO_CHAR(data_adesao, 'YYYY-MM') = %s
  AND valor > 0
ORDER BY data_adesao DESC
"""

SELECT_CHURNS_MES = """
-- Query para buscar churns do mês atual
-- Considera apenas clientes com valor > 0
SELECT
    client_id,
    nome,
    vendedor,
    valor,
    taxa_setup,
    status,
    status_financeiro,
    parcelas_atrasadas,
    data_adesao,
    data_cancelamento,
    pipeline,
    -- Calcular meses de vigência até HOJE
    GREATEST(
        1,
        (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM CURRENT_DATE) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo
FROM clientes_atual
WHERE data_cancelamento >= %s
  AND valor > 0
ORDER BY data_cancelamento DESC
"""

SELECT_CHURNS_BY_MONTH = """
-- Query para buscar churns ATÉ um mês específico
-- Considera apenas clientes com valor > 0
-- Parâmetro: mês no formato YYYY-MM (filtra cancelamentos até o final deste mês)
SELECT
    client_id,
    nome,
    vendedor,
    valor,
    taxa_setup,
    status,
    status_financeiro,
    parcelas_atrasadas,
    data_adesao,
    data_cancelamento,
    pipeline,
    -- Calcular meses de vigência até HOJE
    GREATEST(
        1,
        (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM CURRENT_DATE) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo,
    -- Calcular meses de vigência até o mês de referência
    GREATEST(
        1,
        (EXTRACT(YEAR FROM TO_DATE(%s, 'YYYY-MM')) - EXTRACT(YEAR FROM data_adesao)) * 12 +
        (EXTRACT(MONTH FROM TO_DATE(%s, 'YYYY-MM')) - EXTRACT(MONTH FROM data_adesao)) + 1
    )::int AS meses_ativo_referencia
FROM clientes_atual
WHERE data_cancelamento <= (TO_DATE(%s, 'YYYY-MM') + INTERVAL '1 month - 1 day')::date
  AND valor > 0
ORDER BY data_cancelamento DESC
"""

DASHBOARD_VENDAS_METRICS = """
-- Query para métricas gerais do dashboard de vendas (sem filtro)
WITH metricas AS (
    SELECT
        COUNT(*) as total_clientes,
        COUNT(CASE
            WHEN status NOT IN ('churns', 'cancelados', 'solicitar cancelamento')
            AND COALESCE(pipeline, '') NOT ILIKE '%churns%cancelamentos%'
            AND COALESCE(status_financeiro, '') != 'inadimplente'
            THEN 1
        END) as clientes_ativos,
        COUNT(CASE
            WHEN status_financeiro = 'inadimplente'
            THEN 1
        END) as clientes_inadimplentes,
        COUNT(CASE
            WHEN status IN ('churns', 'cancelados', 'solicitar cancelamento')
            OR pipeline ILIKE '%churns%cancelamentos%'
            THEN 1
        END) as clientes_cancelados,
        COALESCE(SUM(CASE
            WHEN status NOT IN ('churns', 'cancelados', 'solicitar cancelamento')
            AND COALESCE(pipeline, '') NOT ILIKE '%churns%cancelamentos%'
            AND COALESCE(status_financeiro, '') != 'inadimplente'
            THEN valor
            ELSE 0
        END), 0) as mrr_total,
        COALESCE(AVG(CASE
            WHEN status NOT IN ('churns', 'cancelados', 'solicitar cancelamento')
            AND COALESCE(pipeline, '') NOT ILIKE '%churns%cancelamentos%'
            THEN meses_ativo
        END), 0) as avg_meses_ativo
    FROM clientes_atual
    WHERE valor > 0
),
novos_mes AS (
    SELECT COUNT(*) as novos_mes_atual
    FROM clientes_atual
    WHERE data_adesao >= DATE_TRUNC('month', CURRENT_DATE)
      AND valor > 0
      AND status NOT IN ('churns', 'cancelados', 'solicitar cancelamento')
),
churns_mes AS (
    SELECT COUNT(*) as churns_mes_atual
    FROM clientes_atual
    WHERE data_cancelamento >= DATE_TRUNC('month', CURRENT_DATE)
      AND valor > 0
)
SELECT
    m.total_clientes,
    m.clientes_ativos,
    m.clientes_inadimplentes,
    m.clientes_cancelados,
    m.mrr_total,
    m.avg_meses_ativo,
    n.novos_mes_atual,
    c.churns_mes_atual,
    CASE WHEN m.clientes_ativos > 0 THEN ROUND(m.mrr_total / m.clientes_ativos, 2) ELSE 0 END as ticket_medio
FROM metricas m, novos_mes n, churns_mes c
"""

DASHBOARD_VENDAS_METRICS_BY_MONTH = """
-- Query para métricas do dashboard de vendas ATÉ um mês específico
-- Parâmetro: mês no formato YYYY-MM (filtra clientes que aderiram ATÉ o final deste mês)
WITH metricas AS (
    SELECT
        COUNT(*) as total_clientes,
        COUNT(CASE
            WHEN status NOT IN ('churns', 'cancelados', 'solicitar cancelamento')
            AND COALESCE(pipeline, '') NOT ILIKE '%churns%cancelamentos%'
            AND COALESCE(status_financeiro, '') != 'inadimplente'
            THEN 1
        END) as clientes_ativos,
        COUNT(CASE
            WHEN status_financeiro = 'inadimplente'
            THEN 1
        END) as clientes_inadimplentes,
        COUNT(CASE
            WHEN status IN ('churns', 'cancelados', 'solicitar cancelamento')
            OR pipeline ILIKE '%churns%cancelamentos%'
            THEN 1
        END) as clientes_cancelados,
        COALESCE(SUM(CASE
            WHEN status NOT IN ('churns', 'cancelados', 'solicitar cancelamento')
            AND COALESCE(pipeline, '') NOT ILIKE '%churns%cancelamentos%'
            AND COALESCE(status_financeiro, '') != 'inadimplente'
            THEN valor
            ELSE 0
        END), 0) as mrr_total,
        COALESCE(SUM(CASE
            WHEN status NOT IN ('churns', 'cancelados', 'solicitar cancelamento')
            AND COALESCE(pipeline, '') NOT ILIKE '%churns%cancelamentos%'
            AND COALESCE(status_financeiro, '') != 'inadimplente'
            THEN taxa_setup
            ELSE 0
        END), 0) as setup_total,
        COALESCE(AVG(CASE
            WHEN status NOT IN ('churns', 'cancelados', 'solicitar cancelamento')
            AND COALESCE(pipeline, '') NOT ILIKE '%churns%cancelamentos%'
            THEN meses_ativo
        END), 0) as avg_meses_ativo
    FROM clientes_atual
    WHERE valor > 0
      AND data_adesao <= (TO_DATE(%s, 'YYYY-MM') + INTERVAL '1 month - 1 day')::date
),
churns_mes AS (
    SELECT COUNT(*) as churns_mes_atual
    FROM clientes_atual
    WHERE data_cancelamento <= (TO_DATE(%s, 'YYYY-MM') + INTERVAL '1 month - 1 day')::date
      AND valor > 0
)
SELECT
    m.total_clientes,
    m.clientes_ativos,
    m.clientes_inadimplentes,
    m.clientes_cancelados,
    m.mrr_total,
    m.setup_total,
    m.avg_meses_ativo,
    m.total_clientes as novos_mes_atual,
    c.churns_mes_atual,
    CASE WHEN m.clientes_ativos > 0 THEN ROUND(m.mrr_total / m.clientes_ativos, 2) ELSE 0 END as ticket_medio
FROM metricas m, churns_mes c
"""

METRICAS_CLIENTES = """
WITH churns_periodo AS (
    SELECT
        DATE_TRUNC('month', data_cancelamento) AS mes_churn,
        COUNT(client_id) AS clientes_churned
    FROM
        clientes_atual
    WHERE
        data_cancelamento IS NOT NULL
        AND valor > 0
    GROUP BY
        mes_churn
),
entradas_periodo AS (
    SELECT
        DATE_TRUNC('month', data_adesao) AS mes_adesao,
        COUNT(client_id) AS novos_clientes
    FROM
        clientes_atual
    WHERE
        valor > 0
    GROUP BY
        mes_adesao
),
dados_mensais AS (
    -- Etapa 1: Calcula o saldo líquido
    SELECT
        ep.mes_adesao,
        ep.novos_clientes,
        COALESCE(cp.clientes_churned, 0) AS clientes_churned,
        (ep.novos_clientes - COALESCE(cp.clientes_churned, 0)) AS saldo_liquido
    FROM
        entradas_periodo ep
    LEFT JOIN
        churns_periodo cp ON cp.mes_churn = ep.mes_adesao
),
base_acumulada AS (
    -- Etapa 2: Calcula a soma cumulativa (Total de Ativos FINAL do mês)
    SELECT
        dm.*,
        SUM(dm.saldo_liquido) OVER (ORDER BY dm.mes_adesao ASC) AS total_ativos_final_mes
    FROM
        dados_mensais dm
)
SELECT
    TO_CHAR(ba.mes_adesao, 'MM/YYYY') AS mes_referencia,
    ba.novos_clientes,
    ba.clientes_churned,
    ba.total_ativos_final_mes, -- Total de Clientes Ativos no final do mês
    -- Etapa 3: Aplica o LAG sobre a coluna 'total_ativos_final_mes' (que agora é uma coluna simples)
    LAG(ba.total_ativos_final_mes, 1, 0) OVER (
        ORDER BY ba.mes_adesao ASC
    ) AS total_ativos_inicio_mes, -- Base Final do Mês Anterior = Base Inicial do Mês Atual,
    ROUND(ba.clientes_churned / LAG(ba.total_ativos_final_mes) OVER (ORDER BY ba.mes_adesao ASC), 4)*100 as churns_rate,
    ROUND(
    	(ba.total_ativos_final_mes - LAG(ba.total_ativos_final_mes) OVER (ORDER BY ba.mes_adesao ASC))
    	/ LAG(ba.total_ativos_final_mes) OVER (ORDER BY ba.mes_adesao ASC), 4)*100 as growth_rate
FROM
    base_acumulada ba
ORDER BY
    ba.mes_adesao ASC
"""