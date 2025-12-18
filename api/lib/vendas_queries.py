# ============================================================================
# QUERIES DE VENDAS
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