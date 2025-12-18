# ============================================================================
# QUERIES DE HEALTH SCORES
# ============================================================================

PRIMEIRO_PILAR = """
-- Pilar 1: Engajamento e Frequência
WITH acessos AS (
    SELECT
        COALESCE(al.tenant_id, u.tenant_id) AS tenant_id,
        COUNT(CASE WHEN al.created_at >= CURDATE() - INTERVAL 30 DAY THEN 1 END) AS qntd_acessos,
        DATEDIFF(NOW(), MAX(al.created_at)) AS dias_desde_ultimo_acesso,
        COUNT(DISTINCT CASE WHEN al.created_at >= CURDATE() - INTERVAL 30 DAY THEN al.subject_id END) AS usuarios_ativos_30d
    FROM activity_log al
    LEFT JOIN users u ON u.id = al.subject_id
    WHERE al.event = 'login'
    GROUP BY COALESCE(al.tenant_id, u.tenant_id)
)
SELECT
    t.id AS tenant_id,
    COALESCE(a.qntd_acessos, 0) AS qntd_acessos_30d,
    COALESCE(a.dias_desde_ultimo_acesso, 9999) AS dias_desde_ultimo_acesso,
    COALESCE(a.usuarios_ativos_30d, 0) AS usuarios_ativos_30d,
    CASE -- tipo_equipe baseado no tamanho da equipe
        WHEN COALESCE(a.usuarios_ativos_30d, 0) <= 2 THEN 'Pequena'
        WHEN COALESCE(a.usuarios_ativos_30d, 0) <= 5 THEN 'Média'
        WHEN COALESCE(a.usuarios_ativos_30d, 0) <= 9 THEN 'Grande'
        ELSE 'Extra grande'
    END AS tipo_equipe,
    ROUND((
        CASE -- score_ultimo_acesso (igual para todos)
            WHEN a.dias_desde_ultimo_acesso <= 3 THEN 1
            WHEN a.dias_desde_ultimo_acesso <= 7 THEN 0.9
            WHEN a.dias_desde_ultimo_acesso <= 14 THEN 0.6
            WHEN a.dias_desde_ultimo_acesso <= 30 THEN 0.2
            ELSE 0
        END +
        CASE -- score_qntd_acessos (proporcional ao tamanho da equipe, ajustado para atividade semanal consistente)
            WHEN COALESCE(a.usuarios_ativos_30d, 0) <= 2 THEN -- Pequena equipe (1-2 usuários)
                CASE WHEN a.qntd_acessos >= 25 THEN 1.2 WHEN a.qntd_acessos >= 12 THEN 1 WHEN a.qntd_acessos >= 6 THEN 0.7 WHEN a.qntd_acessos >= 3 THEN 0.5 WHEN a.qntd_acessos >= 2 THEN 0.3 ELSE 0.0 END
            WHEN COALESCE(a.usuarios_ativos_30d, 0) <= 5 THEN -- Média equipe (3-5 usuários)
                CASE WHEN a.qntd_acessos >= 40 THEN 1.2 WHEN a.qntd_acessos >= 20 THEN 1 WHEN a.qntd_acessos >= 10 THEN 0.7 WHEN a.qntd_acessos >= 5 THEN 0.5 WHEN a.qntd_acessos >= 3 THEN 0.3 ELSE 0.0 END
            WHEN COALESCE(a.usuarios_ativos_30d, 0) <= 9 THEN -- Grande equipe (6-9 usuários)
                CASE WHEN a.qntd_acessos >= 70 THEN 1.2 WHEN a.qntd_acessos >= 35 THEN 1 WHEN a.qntd_acessos >= 18 THEN 0.7 WHEN a.qntd_acessos >= 9 THEN 0.5 WHEN a.qntd_acessos >= 5 THEN 0.3 ELSE 0.0 END
            ELSE -- Extra grande equipe (10+ usuários)
                CASE WHEN a.qntd_acessos >= 95 THEN 1.2 WHEN a.qntd_acessos >= 48 THEN 1 WHEN a.qntd_acessos >= 24 THEN 0.7 WHEN a.qntd_acessos >= 12 THEN 0.5 WHEN a.qntd_acessos >= 7 THEN 0.3 ELSE 0.0 END
        END
        ) / 2, 2) AS score_engajamento
FROM tenants t
LEFT JOIN acessos a ON t.id = a.tenant_id
WHERE t.type = 'normal'
ORDER BY score_engajamento DESC;
"""

SEGUNDO_PILAR = """
WITH
-- 1. Calcula o Estoque Atual (Usando NOT EXISTS para performance máxima)
estoque_atual AS (
    SELECT
        ie.tenant_id,
        COUNT(ie.id) as total_veiculos
    FROM inventory_entries ie
    WHERE ie.deleted_at IS NULL
      AND ie.status = 'active'
      -- Verifica se NÃO existe uma saída ativa para este veículo
      AND NOT EXISTS (
          SELECT 1
          FROM inventory_outs io
          WHERE io.vehicle_id = ie.vehicle_id
          AND io.deleted_at IS NULL
      )
    GROUP BY ie.tenant_id
),
-- 2. Calcula Métricas de Entrada (Histórico)
metricas_entradas AS (
    SELECT
        tenant_id,
        COUNT(CASE WHEN created_at >= CURDATE() - INTERVAL 30 DAY THEN 1 END) AS qntd_entradas_30d,
        DATEDIFF(NOW(), MAX(created_at)) AS dias_desde_ultima_entrada
    FROM inventory_entries
    WHERE deleted_at IS NULL
    GROUP BY tenant_id
),
-- 3. Calcula Métricas de Saída (Histórico)
metricas_saidas AS (
    SELECT
        tenant_id,
        COUNT(CASE WHEN created_at >= CURDATE() - INTERVAL 30 DAY THEN 1 END) AS qntd_saidas_30d,
        DATEDIFF(NOW(), MAX(created_at)) AS dias_desde_ultima_saida
    FROM inventory_outs
    WHERE deleted_at IS NULL
    GROUP BY tenant_id
)
-- 4. Consolidação e Cálculo do Score
SELECT
    t.id AS tenant_id,
    t.name,
    COALESCE(ea.total_veiculos, 0) AS estoque_total,
    -- Visualização do Porte (Para fins de debug/interface)
    CASE
        WHEN COALESCE(ea.total_veiculos, 0) <= 15 THEN 'Pequeno'
        WHEN COALESCE(ea.total_veiculos, 0) <= 50 THEN 'Médio'
        ELSE 'Grande'
    END AS porte_loja,
    -- Métricas Brutas
    COALESCE(me.qntd_entradas_30d, 0) AS qntd_entradas_30d,
    COALESCE(me.dias_desde_ultima_entrada, 999) AS dias_desde_ultima_entrada,
    COALESCE(ms.qntd_saidas_30d, 0) AS qntd_saidas_30d,
    COALESCE(ms.dias_desde_ultima_saida, 999) AS dias_desde_ultima_saida,
    -- SCORE CALCULADO (0 a 1)
    ROUND((
        -- A. Recência Entrada (Peso igual para todos)
        COALESCE(CASE
            WHEN me.dias_desde_ultima_entrada <= 5 THEN 1.0
            WHEN me.dias_desde_ultima_entrada <= 10 THEN 0.8
            WHEN me.dias_desde_ultima_entrada <= 20 THEN 0.5
            WHEN me.dias_desde_ultima_entrada <= 30 THEN 0.2
            ELSE 0.0 -- Penalidade severa se não repor estoque há muito tempo
        END, 0) +
        -- B. Volume Entrada (Proporcional ao Porte)
        CASE
            -- Pequeno (<= 15 carros)
            WHEN COALESCE(ea.total_veiculos, 0) <= 15 THEN
                CASE WHEN me.qntd_entradas_30d >= 4 THEN 1.2 WHEN me.qntd_entradas_30d >= 2 THEN 0.8 WHEN me.qntd_entradas_30d >= 1 THEN 0.4 ELSE 0.0 END
            -- Médio (16-50 carros)
            WHEN COALESCE(ea.total_veiculos, 0) <= 50 THEN
                CASE WHEN me.qntd_entradas_30d >= 10 THEN 1.2 WHEN me.qntd_entradas_30d >= 5 THEN 0.8 WHEN me.qntd_entradas_30d >= 2 THEN 0.4 ELSE 0.0 END
            -- Grande (> 50 carros)
            ELSE
                CASE WHEN me.qntd_entradas_30d >= 30 THEN 1.2 WHEN me.qntd_entradas_30d >= 15 THEN 0.8 WHEN me.qntd_entradas_30d >= 7 THEN 0.4 ELSE 0.0 END
        END +
        -- C. Recência Saída (Peso igual para todos)
        COALESCE(CASE
            WHEN ms.dias_desde_ultima_saida <= 3 THEN 1.0
            WHEN ms.dias_desde_ultima_saida <= 7 THEN 0.8
            WHEN ms.dias_desde_ultima_saida <= 15 THEN 0.5
            WHEN ms.dias_desde_ultima_saida <= 30 THEN 0.2
            ELSE 0.0
        END, 0) +
        -- D. Volume Saída (Proporcional ao Porte)
        CASE
            -- Pequeno
            WHEN COALESCE(ea.total_veiculos, 0) <= 15 THEN
                CASE WHEN ms.qntd_saidas_30d >= 3 THEN 1.2 WHEN ms.qntd_saidas_30d >= 2 THEN 0.8 WHEN ms.qntd_saidas_30d >= 1 THEN 0.4 ELSE 0.0 END
            -- Médio
            WHEN COALESCE(ea.total_veiculos, 0) <= 50 THEN
                CASE WHEN ms.qntd_saidas_30d >= 8 THEN 1.2 WHEN ms.qntd_saidas_30d >= 4 THEN 0.8 WHEN ms.qntd_saidas_30d >= 2 THEN 0.4 ELSE 0.0 END
            -- Grande
            ELSE
                CASE WHEN ms.qntd_saidas_30d >= 25 THEN 1.2 WHEN ms.qntd_saidas_30d >= 12 THEN 0.8 WHEN ms.qntd_saidas_30d >= 6 THEN 0.4 ELSE 0.0 END
        END
    ) / 4, 2) AS score_movimentacao_estoque
FROM tenants t
LEFT JOIN estoque_atual ea ON ea.tenant_id = t.id
LEFT JOIN metricas_entradas me ON me.tenant_id = t.id
LEFT JOIN metricas_saidas ms ON ms.tenant_id = t.id
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