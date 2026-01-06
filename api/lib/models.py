from pydantic import BaseModel, validator
from typing import Optional, List
import re


def validate_cpf(cpf: str) -> bool:
    """Valida CPF usando algoritmo oficial."""
    cpf = ''.join(filter(str.isdigit, cpf))

    if len(cpf) != 11:
        return False

    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False

    # Calcula primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    dv1 = 0 if resto == 10 else resto

    # Calcula segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    dv2 = 0 if resto == 10 else resto

    return cpf[-2:] == f"{dv1}{dv2}"


def validate_cnpj(cnpj: str) -> bool:
    """Valida CNPJ usando algoritmo oficial."""
    cnpj = ''.join(filter(str.isdigit, cnpj))

    if len(cnpj) != 14:
        return False

    # Verifica se todos os dígitos são iguais
    if cnpj == cnpj[0] * 14:
        return False

    # Calcula primeiro dígito verificador
    pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos[i] for i in range(12))
    resto = soma % 11
    dv1 = 0 if resto < 2 else 11 - resto

    # Calcula segundo dígito verificador
    pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos[i] for i in range(13))
    resto = soma % 11
    dv2 = 0 if resto < 2 else 11 - resto

    return cnpj[-2:] == f"{dv1}{dv2}"


def validate_cpf_cnpj(value: str) -> str:
    """Valida e limpa CPF ou CNPJ."""
    cleaned = ''.join(filter(str.isdigit, value))

    if len(cleaned) == 11:
        if not validate_cpf(cleaned):
            raise ValueError(f'CPF inválido: {value}')
    elif len(cleaned) == 14:
        if not validate_cnpj(cleaned):
            raise ValueError(f'CNPJ inválido: {value}')
    else:
        raise ValueError(f'CPF/CNPJ deve ter 11 (CPF) ou 14 (CNPJ) dígitos. Recebido: {len(cleaned)} dígitos')

    return cleaned

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
    usuarios_ativos_30d: int = 0
    tipo_equipe: Optional[str] = None
    score_engajamento: float = 0.0 # Pilar 1
    estoque_total: int = 0
    porte_loja: Optional[str] = None
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


# ============================================================================
# PAGINATION MODELS
# ============================================================================

class PaginationParams(BaseModel):
    """Parâmetros de paginação."""
    offset: int = 0
    limit: int = 100


class PaginatedResponse(BaseModel):
    """Resposta paginada."""
    has_more: bool = False
    total_count: int = 0
    limit: int = 100
    offset: int = 0
    data: List = []