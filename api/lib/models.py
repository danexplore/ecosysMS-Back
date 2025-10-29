from pydantic import BaseModel
from typing import Optional, List

class Cliente(BaseModel):
    """Modelo Pydantic para clientes vindo do banco."""
    client_id: int
    nome: Optional[str] = None
    razao_social: Optional[str] = None
    cnpj: Optional[int] = None
    valor: float = 0.0
    vendedor: Optional[str] = None
    cs: Optional[str] = None
    status: Optional[str] = None
    pipeline: Optional[str] = None
    data_adesao: Optional[str] = None
    data_start_onboarding: Optional[str] = None
    data_end_onboarding: Optional[str] = None
    tmo: Optional[int] = None
    data_cancelamento: Optional[str] = None
    motivos_churn: Optional[str] = None
    descricao_cancelamento: Optional[str] = None
    criado_em: Optional[str] = None
    atualizado_em: Optional[str] = None
    
class ClientScoreHealth(BaseModel):
    tenant_id: int
    cnpj: Optional[int] = None
    qntd_acessos_30d: int = 0
    dias_desde_ultimo_acesso: int = 9999
    score_engajamento: float = 0.0 # Pilar 1
    qntd_entradas_30d: int = 0
    dias_desde_ultima_entrada: int = 9999
    qntd_saidas_30d: int = 0
    dias_desde_ultima_saida: int = 9999
    score_movimentacao_estoque: float = 0.0 # Pilar 2
    qntd_leads_30d: int = 0
    dias_desde_ultimo_lead: int = 9999
    score_crm: float = 0.0 # Pilar 3
    score_adoption: float = 0.0 # Pilar 4
    score_total: float = 0.0 # SSC
    categoria: Optional[str] = None

class ClientLogins(BaseModel):
    tenant_id: int
    cnpj: Optional[int] = None
    logins: List[str] = []  # Lista de timestamps de logins