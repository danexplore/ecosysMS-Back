LOGINS_BY_TENANT = """
-- Query para buscar todos os logins de um tenant nos últimos 30 dias
SELECT
    al.id,
    COALESCE(al.tenant_id, u.tenant_id) AS tenant_id,
    al.subject_id,
    u.name as usuario_nome,
    u.email as usuario_email,
    al.created_at as data_login,
    DATE(al.created_at) as data,
    TIME(al.created_at) as hora
FROM activity_log al
LEFT JOIN users u ON u.id = al.subject_id
WHERE al.event = 'login'
    AND COALESCE(al.tenant_id, u.tenant_id) = %s
    AND al.created_at >= CURDATE() - INTERVAL 30 DAY
ORDER BY al.created_at DESC
"""

SELECT_CLIENTES = """
select
  *
from clientes_atual
order by data_adesao desc
"""

PRIMEIRO_PILAR = """
-- Pilar 1: Engajamento e Frequência
WITH acessos AS (
	SELECT
		COALESCE(al.tenant_id, u.tenant_id) AS tenant_id,
		COUNT(CASE WHEN al.created_at >= CURDATE() - INTERVAL 30 DAY THEN 1 END) AS qntd_acessos,
		DATEDIFF(NOW(), MAX(al.created_at)) AS dias_desde_ultimo_acesso
	FROM activity_log al
	LEFT JOIN users u ON u.id = al.subject_id
	WHERE al.event = 'login'
	GROUP BY COALESCE(al.tenant_id, u.tenant_id)
)
SELECT
	t.id AS tenant_id,
	COALESCE(a.qntd_acessos, 0) AS qntd_acessos_30d,
	COALESCE(a.dias_desde_ultimo_acesso, 9999) AS dias_desde_ultimo_acesso,
	ROUND((
		CASE -- score_ultimo_acesso
			WHEN a.dias_desde_ultimo_acesso <= 3 THEN 1
			WHEN a.dias_desde_ultimo_acesso <= 7 THEN 0.9
			WHEN a.dias_desde_ultimo_acesso <= 14 THEN 0.6
			WHEN a.dias_desde_ultimo_acesso <= 30 THEN 0.2
			ELSE 0
		END +
		CASE -- score_qntd_acessos
			WHEN a.qntd_acessos > 75 THEN 1.2
			WHEN a.qntd_acessos > 40 THEN 1
			WHEN a.qntd_acessos > 25 THEN 0.7
			WHEN a.qntd_acessos > 11 THEN 0.5
			WHEN a.qntd_acessos > 6 THEN 0.3
			WHEN a.qntd_acessos > 1 THEN 0.15
			ELSE 0
		END
		) / 2, 2) AS score_engajamento
FROM tenants t
LEFT JOIN acessos a ON t.id = a.tenant_id
WHERE t.type = 'normal'
ORDER BY score_engajamento DESC;
"""

SEGUNDO_PILAR = """
-- Pilar 2: Movimentação de Estoque
WITH entradas AS (
  SELECT
    tenant_id,
    COUNT(CASE WHEN created_at >= CURDATE() - INTERVAL 30 DAY THEN 1 END) AS qntd_entradas_30d,
    DATEDIFF(NOW(), MAX(created_at)) AS dias_desde_ultima_entrada
  FROM inventory_entries
  WHERE deleted_at IS NULL
  GROUP BY tenant_id
),
saidas AS (
  SELECT
    tenant_id,
    COUNT(CASE WHEN created_at >= CURDATE() - INTERVAL 30 DAY THEN 1 END) AS qntd_saidas_30d,
    DATEDIFF(NOW(), MAX(created_at)) AS dias_desde_ultima_saida
  FROM inventory_outs
  WHERE deleted_at IS NULL
  GROUP BY tenant_id
)
SELECT
  t.id AS tenant_id,
  COALESCE(e.qntd_entradas_30d, 0) AS qntd_entradas_30d,
  COALESCE(e.dias_desde_ultima_entrada, 9999) AS dias_desde_ultima_entrada,
  COALESCE(s.qntd_saidas_30d, 0) AS qntd_saidas_30d,
  COALESCE(s.dias_desde_ultima_saida, 9999) AS dias_desde_ultima_saida,
  ROUND((
    COALESCE(
      CASE 
        WHEN e.dias_desde_ultima_entrada <= 3 THEN 1
        WHEN e.dias_desde_ultima_entrada <= 7 THEN 0.85
        WHEN e.dias_desde_ultima_entrada <= 14 THEN 0.6
        WHEN e.dias_desde_ultima_entrada <= 30 THEN 0.3
        ELSE 0
      END, 0
    ) +
    CASE 
      WHEN e.qntd_entradas_30d > 40 THEN 1.2
      WHEN e.qntd_entradas_30d > 20 THEN 1
      WHEN e.qntd_entradas_30d > 9 THEN 0.7
      WHEN e.qntd_entradas_30d > 3 THEN 0.5
      WHEN e.qntd_entradas_30d > 0 THEN 0.33
      ELSE 0
    END +
    COALESCE(
      CASE 
        WHEN s.dias_desde_ultima_saida <= 3 THEN 1
        WHEN s.dias_desde_ultima_saida <= 7 THEN 0.85
        WHEN s.dias_desde_ultima_saida <= 14 THEN 0.6
        WHEN s.dias_desde_ultima_saida <= 30 THEN 0.3
        ELSE 0
      END, 0
    ) +
    CASE 
      WHEN s.qntd_saidas_30d > 40 THEN 1.2
      WHEN s.qntd_saidas_30d > 20 THEN 1
      WHEN s.qntd_saidas_30d > 9 THEN 0.7
      WHEN s.qntd_saidas_30d > 3 THEN 0.5
      WHEN s.qntd_saidas_30d > 0 THEN 0.33
      ELSE 0
    END
  ) / 4, 2) AS score_movimentacao_estoque
FROM tenants t
LEFT JOIN entradas e ON e.tenant_id = t.id
LEFT JOIN saidas s ON s.tenant_id = t.id
WHERE t.type = 'normal'
ORDER BY score_movimentacao_estoque DESC;
"""

TERCEIRO_PILAR = """
-- Pilar 3: CRM
WITH leads AS (
	SELECT
		c.tenant_id,
		COUNT(CASE WHEN created_at >= CURDATE() - INTERVAL 30 DAY THEN 1 END) AS qntd_leads,
		DATEDIFF(NOW(), MAX(c.created_at)) AS dias_desde_ultimo_lead
	FROM cards c
	WHERE c.deleted_at IS NULL
	GROUP BY c.tenant_id
)
SELECT
	t.id AS tenant_id,
	COALESCE(l.qntd_leads, 0) AS qntd_leads_30d,
	COALESCE(l.dias_desde_ultimo_lead, 9999) AS dias_desde_ultimo_lead,
	ROUND((
	CASE -- score_ultimo_lead
		WHEN l.dias_desde_ultimo_lead <= 3 THEN 1
		WHEN l.dias_desde_ultimo_lead <= 7 THEN 0.9
		WHEN l.dias_desde_ultimo_lead <= 14 THEN 0.6
		WHEN l.dias_desde_ultimo_lead <= 30 THEN 0.2
		ELSE 0
	END + CASE -- score_qntd_leads
		WHEN l.qntd_leads > 75 THEN 1.2
		WHEN l.qntd_leads > 40 THEN 1
		WHEN l.qntd_leads > 25 THEN 0.7
		WHEN l.qntd_leads > 11 THEN 0.5
		WHEN l.qntd_leads > 6 THEN 0.3
		WHEN l.qntd_leads > 1 THEN 0.15
		ELSE 0
	END) / 2, 2) AS score_crm
FROM tenants t 
LEFT JOIN leads l ON t.id = l.tenant_id
WHERE t.type = 'normal'
ORDER BY score_crm DESC;
"""

QUARTO_PILAR = """
-- Pilar 4: Adoção
WITH status_econversa AS (
	SELECT
		t.id AS tenant_id,
		eic.name,
		eic.status,
		eic.created_at,
		eic.updated_at
	FROM econversa_instance_configurations eic
	LEFT JOIN tenants t ON eic.name = t.slug
	WHERE t.id IS NOT NULL
),
econversa_adoption AS (
	SELECT
		em.tenant_id,
		0.3 AS status
	FROM econversa_messages em
	LEFT JOIN status_econversa se ON em.tenant_id = se.tenant_id
	WHERE se.status = 'open'
	GROUP BY tenant_id
	HAVING COUNT(CASE WHEN em.created_at >= CURDATE() - INTERVAL 15 DAY THEN 1 END) > 0
),
integrator_adoption AS (
	SELECT
		tenant_id,
		COUNT(CASE WHEN created_at >= CURDATE() - INTERVAL 30 DAY THEN 1 END) AS qntd_anuncios,
		0.4 AS status
	FROM integrator_ads
	WHERE integrator_id NOT IN (13, 3)
	GROUP BY tenant_id
	HAVING qntd_anuncios > 0
),
reports_adoption AS (
	SELECT
		tenant_id,
		COUNT(CASE WHEN created_at >= CURDATE() - INTERVAL 30 DAY THEN 1 END) AS qntd_relatorios,
		0.1 AS status
	FROM reports 
	GROUP BY tenant_id
	HAVING qntd_relatorios > 0
),
contracts_adoption AS (
	SELECT
		tenant_id,
		COUNT(CASE WHEN created_at >= CURDATE() - INTERVAL 30 DAY THEN 1 END) AS qntd_contratos,
		0.2 AS status
	FROM contracts
	GROUP BY tenant_id
	HAVING qntd_contratos >= 2
)
SELECT 
	t.id AS tenant_id,
	ea.status AS econversa_status,
	ia.status AS ads_status,
	ra.status AS reports_status,
	ca.status AS contracts_status,
	COALESCE(ea.status, 0) +
	COALESCE(ia.status, 0) +
	COALESCE(ra.status, 0) +
	COALESCE(ca.status, 0) AS score_adoption
FROM tenants t
LEFT JOIN econversa_adoption ea ON t.id = ea.tenant_id
LEFT JOIN integrator_adoption ia ON t.id = ia.tenant_id
LEFT JOIN reports_adoption ra ON t.id = ra.tenant_id
LEFT JOIN contracts_adoption ca ON t.id = ca.tenant_id
WHERE t.`type` = 'normal'
ORDER BY score_adoption DESC;
"""

ECONVERSA_STATUS = """
SELECT
	t.id,
	IFNULL(eic.status, 'conecting') AS econversa_connected
FROM tenants t
LEFT JOIN econversa_instance_configurations eic ON t.slug = eic.name
"""

INTEGRATORS_CONNECTED = """
SELECT
    tenant_id,
    GROUP_CONCAT(
        CASE integrator_id
            WHEN 1  THEN 'WEBMOTORS'
            WHEN 2  THEN 'KBB'
            WHEN 4  THEN 'FIPE'
            WHEN 5  THEN 'OLX'
            WHEN 6  THEN 'EMAIL'
            WHEN 7  THEN 'ControlStock'
            WHEN 8  THEN 'MOBIAUTO'
            WHEN 9  THEN 'AUTOAVALIAR'
            WHEN 11 THEN 'JSONFEED'
            WHEN 12 THEN 'MERCADO_LIVRE'
            WHEN 14 THEN 'META'
            WHEN 15 THEN 'Autoline'
            WHEN 16 THEN 'CREDERE'
        END
        ORDER BY integrator_id
        SEPARATOR ', '
    ) AS integrators_connected
FROM integrator_configurations
WHERE deleted_at IS NULL
  AND integrator_id NOT IN (3, 13)
GROUP BY tenant_id;
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

# ============================================================================
# QUERIES DE VENDAS E COMISSÕES
# ============================================================================

SELECT_VENDEDORES = """
-- Query para buscar todos os vendedores ativos
SELECT
    id,
    name,
    email
FROM vendedores
ORDER BY name ASC
"""

SELECT_CLIENTES_COMISSAO = """
-- Query para buscar todos os clientes para cálculo de comissão
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
    meses_ativo
FROM clientes_atual
WHERE valor > 0
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
    meses_ativo
FROM clientes_atual
WHERE status_financeiro = 'inadimplente'
  AND valor > 0
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
    meses_ativo
FROM clientes_atual
WHERE data_adesao >= %s
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
    meses_ativo
FROM clientes_atual
WHERE data_cancelamento >= %s
  AND valor > 0
ORDER BY data_cancelamento DESC
"""

DASHBOARD_VENDAS_METRICS = """
-- Query para métricas gerais do dashboard de vendas
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
