# ============================================================================
# QUERIES SQL - INADIMPLÊNCIA E COMISSÕES
# ============================================================================

# Buscar comissões pendentes detalhadas
BUSCAR_COMISSOES_PENDENTES = """
SELECT * FROM vw_comissoes_pendentes_detalhado
WHERE (%s IS NULL OR vendedor_id = %s)
  AND (%s IS NULL OR status = %s)
ORDER BY mes_referencia ASC
LIMIT %s
"""

# Buscar resumo de comissões por vendedor
BUSCAR_RESUMO_COMISSOES = """
SELECT * FROM vw_comissoes_fifo_resumo
WHERE (%s IS NULL OR vendedor_id = %s)
"""

# Inserir comissão pendente (com upsert)
INSERIR_COMISSAO_PENDENTE = """
INSERT INTO comissoes_pendentes (
    cnpj, razao_social, vendedor_id, vendedor_nome, mes_referencia,
    parcela_numero, valor_mrr, percentual_aplicado, valor_comissao,
    status, motivo_bloqueio, data_bloqueio
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (cnpj, mes_referencia) DO NOTHING
"""

# Atualizar status de comissões por CNPJ
ATUALIZAR_COMISSOES_STATUS = """
UPDATE comissoes_pendentes
SET status = %s, motivo_bloqueio = %s, updated_at = %s
WHERE cnpj = %s AND status = 'bloqueada'
"""

# Buscar comissões bloqueadas por CNPJ
BUSCAR_COMISSOES_BLOQUEADAS_POR_CNPJ = """
SELECT id FROM comissoes_pendentes
WHERE cnpj = %s AND status = 'bloqueada'
ORDER BY mes_referencia ASC
LIMIT %s
"""

# Atualizar comissão específica para paga
ATUALIZAR_COMISSAO_PARA_PAGA = """
UPDATE comissoes_pendentes
SET status = 'paga', data_liberacao = %s, updated_at = %s
WHERE id = %s
"""

# Buscar comissões liberadas
BUSCAR_COMISSOES_LIBERADAS = """
SELECT * FROM vw_comissoes_pendentes_detalhado
WHERE status = 'paga'
  AND (%s IS NULL OR vendedor_id = %s)
ORDER BY data_liberacao DESC
LIMIT %s
"""

# Marcar comissões como perdidas
MARCAR_COMISSOES_PERDIDAS = """
UPDATE comissoes_pendentes
SET status = 'perdida', motivo_bloqueio = %s, updated_at = %s
WHERE cnpj = %s AND status = 'bloqueada'
"""

# Liberar comissões por FIFO (usado na função de regularização)
LIBERAR_COMISSOES_FIFO = """
UPDATE comissoes_pendentes
SET status = 'paga', data_liberacao = %s, updated_at = %s
WHERE id IN (
    SELECT id FROM comissoes_pendentes
    WHERE cnpj = %s AND status = 'bloqueada'
    ORDER BY mes_referencia ASC
    LIMIT %s
)
"""