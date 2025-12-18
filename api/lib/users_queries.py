# ============================================================================
# QUERIES DE USUÁRIOS
# ============================================================================

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

SELECT_CS_USERS = """
-- Query para buscar e-mails dos CS's específicos
SELECT
    id,
    name,
    email
FROM users
WHERE id IN (13090515, 13393851, 13406671, 13480695)
ORDER BY name
"""