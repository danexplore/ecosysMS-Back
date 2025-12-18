# ============================================================================
# QUERIES DE PAGAMENTOS - BASE PARA CÁLCULO DE COMISSÕES
# ============================================================================

SELECT_HISTORICO_PAGAMENTOS_POR_CLIENTE = """
-- Busca histórico de pagamentos por cliente com dados do vendedor
SELECT
    hp.cnpj,
    hp.loja,
    hp.vencimento,
    hp.data_pagamento,
    hp.parcela,
    hp.valor,
    hp.descricao_status,
    ck.id as cliente_id,
    ck.nome as cliente_nome,
    ck.vendedor,
    ck.data_adesao,
    ck.data_cancelamento,
    ck.valor as mrr,
    ck.taxa_setup
FROM historico_pagamentos hp
JOIN companies_kommo co ON co.cnpj = hp.cnpj
JOIN clientes_kommo ck ON ck.company_id = co.id
WHERE hp.data_pagamento IS NOT NULL
ORDER BY hp.cnpj, hp.vencimento
"""

SELECT_PARCELAS_PAGAS_POR_VENDEDOR = """
-- Agrupa parcelas pagas por vendedor para cálculo de comissões
-- O mês de comissão é o mês SEGUINTE ao vencimento da parcela paga
SELECT
    ck.vendedor,
    ck.id as cliente_id,
    ck.nome as cliente_nome,
    ck.data_adesao,
    ck.data_cancelamento,
    ck.valor as mrr,
    ck.taxa_setup,
    co.cnpj,
    COUNT(hp.id) as total_parcelas_pagas,
    ARRAY_AGG(DISTINCT TO_CHAR(hp.vencimento, 'YYYY-MM') ORDER BY TO_CHAR(hp.vencimento, 'YYYY-MM')) as meses_parcelas_pagas,
    MIN(hp.vencimento) as primeira_parcela_paga,
    MAX(hp.vencimento) as ultima_parcela_paga
FROM clientes_kommo ck
JOIN companies_kommo co ON co.id = ck.company_id
LEFT JOIN historico_pagamentos hp ON hp.cnpj = co.cnpj AND hp.data_pagamento IS NOT NULL
WHERE ck.data_adesao IS NOT NULL
  AND ck.vendedor IS NOT NULL
  AND ck.vendedor NOT IN ('Não identificado', '')
GROUP BY ck.vendedor, ck.id, ck.nome, ck.data_adesao, ck.data_cancelamento, ck.valor, ck.taxa_setup, co.cnpj
ORDER BY ck.vendedor, ck.data_adesao
"""

SELECT_PARCELAS_PAGAS_POR_MES_COMISSAO = """
-- Busca parcelas pagas que geram comissão para um mês específico
-- Mês de comissão = mês seguinte ao vencimento da parcela
SELECT
    ck.vendedor,
    ck.id as cliente_id,
    ck.nome as cliente_nome,
    ck.data_adesao,
    ck.data_cancelamento,
    ck.valor as mrr,
    ck.taxa_setup,
    co.cnpj,
    hp.vencimento,
    hp.data_pagamento,
    hp.parcela as numero_parcela,
    -- Calcular posição no ciclo de 7 meses (0-6)
    -- Mês de comissão é mês seguinte ao vencimento, então posição = meses entre adesão e vencimento
    EXTRACT(YEAR FROM hp.vencimento) * 12 + EXTRACT(MONTH FROM hp.vencimento)
    - (EXTRACT(YEAR FROM ck.data_adesao) * 12 + EXTRACT(MONTH FROM ck.data_adesao)) as posicao_ciclo
FROM clientes_kommo ck
JOIN companies_kommo co ON co.id = ck.company_id
JOIN historico_pagamentos hp ON hp.cnpj = co.cnpj AND hp.data_pagamento IS NOT NULL
WHERE ck.data_adesao IS NOT NULL
  AND ck.vendedor IS NOT NULL
  AND ck.vendedor NOT IN ('Não identificado', '')
  -- Filtrar parcelas cujo mês de comissão (mês seguinte ao vencimento) é o mês informado
  AND TO_CHAR(hp.vencimento + INTERVAL '1 month', 'YYYY-MM') = %s
  -- Limitar ao ciclo de 7 meses (posição 0-6)
  AND (EXTRACT(YEAR FROM hp.vencimento) * 12 + EXTRACT(MONTH FROM hp.vencimento)
       - (EXTRACT(YEAR FROM ck.data_adesao) * 12 + EXTRACT(MONTH FROM ck.data_adesao))) BETWEEN 0 AND 6
ORDER BY ck.vendedor, ck.data_adesao, hp.vencimento
"""