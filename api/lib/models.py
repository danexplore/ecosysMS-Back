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
# ASAAS MODELS - Integração com Gateway de Pagamentos
# ============================================================================

from enum import Enum
from datetime import datetime, date
from decimal import Decimal


class PaymentStatus(str, Enum):
    """Status de pagamento do Asaas."""
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    CONFIRMED = "CONFIRMED"
    OVERDUE = "OVERDUE"
    REFUNDED = "REFUNDED"
    RECEIVED_IN_CASH = "RECEIVED_IN_CASH"
    REFUND_REQUESTED = "REFUND_REQUESTED"
    CHARGEBACK_REQUESTED = "CHARGEBACK_REQUESTED"
    CHARGEBACK_DISPUTE = "CHARGEBACK_DISPUTE"
    AWAITING_CHARGEBACK_REVERSAL = "AWAITING_CHARGEBACK_REVERSAL"
    DUNNING_REQUESTED = "DUNNING_REQUESTED"
    DUNNING_RECEIVED = "DUNNING_RECEIVED"
    AWAITING_RISK_ANALYSIS = "AWAITING_RISK_ANALYSIS"


class BillingType(str, Enum):
    """Tipo de cobrança do Asaas."""
    BOLETO = "BOLETO"
    CREDIT_CARD = "CREDIT_CARD"
    PIX = "PIX"
    UNDEFINED = "UNDEFINED"


class SubscriptionCycle(str, Enum):
    """Ciclo de cobrança de assinatura."""
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMIANNUALLY = "SEMIANNUALLY"
    YEARLY = "YEARLY"


class SubscriptionStatus(str, Enum):
    """Status de assinatura."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"


# ============================================================================
# CUSTOMER MODELS
# ============================================================================

class AddressModel(BaseModel):
    """Modelo de endereço."""
    street: Optional[str] = None
    number: Optional[str] = None
    complement: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None


class AsaasCustomerCreate(BaseModel):
    """Modelo para criar cliente no Asaas."""
    name: str
    cpf_cnpj: str
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    address: Optional[AddressModel] = None
    external_reference: Optional[str] = None
    notification_disabled: bool = False


class AsaasCustomerResponse(BaseModel):
    """Modelo de resposta de cliente do Asaas."""
    id: str
    name: str
    cpf_cnpj: str
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    asaas_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================================================
# PRODUCT MODELS
# ============================================================================

class AsaasProductCreate(BaseModel):
    """Modelo para criar produto."""
    name: str
    price: Decimal
    cycle: SubscriptionCycle = SubscriptionCycle.MONTHLY
    description: Optional[str] = None
    active: bool = True


class AsaasProductResponse(BaseModel):
    """Modelo de resposta de produto."""
    id: str
    name: str
    price: Decimal
    cycle: SubscriptionCycle
    description: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = None


# ============================================================================
# PAYMENT MODELS
# ============================================================================

class AsaasPaymentCreate(BaseModel):
    """Modelo para criar cobrança."""
    customer_id: str
    value: Decimal
    due_date: date
    billing_type: BillingType = BillingType.UNDEFINED
    description: Optional[str] = None
    external_reference: Optional[str] = None
    installment_count: Optional[int] = None
    installment_value: Optional[Decimal] = None


class AsaasPaymentResponse(BaseModel):
    """Modelo de resposta de cobrança."""
    id: str
    asaas_id: str
    customer_id: str
    value: Decimal
    status: PaymentStatus
    billing_type: BillingType
    due_date: date
    payment_date: Optional[datetime] = None
    invoice_url: Optional[str] = None
    bank_slip_url: Optional[str] = None
    pix_qr_code: Optional[str] = None
    pix_copy_paste: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class AsaasPaymentUpdate(BaseModel):
    """Modelo para atualizar cobrança."""
    value: Optional[Decimal] = None
    due_date: Optional[date] = None
    description: Optional[str] = None


# ============================================================================
# SUBSCRIPTION MODELS
# ============================================================================

class AsaasSubscriptionCreate(BaseModel):
    """Modelo para criar assinatura."""
    customer_id: str
    product_id: Optional[str] = None
    value: Decimal
    next_due_date: date
    cycle: SubscriptionCycle = SubscriptionCycle.MONTHLY
    billing_type: BillingType = BillingType.UNDEFINED
    description: Optional[str] = None
    external_reference: Optional[str] = None


class AsaasSubscriptionResponse(BaseModel):
    """Modelo de resposta de assinatura."""
    id: str
    asaas_id: str
    customer_id: str
    product_id: Optional[str] = None
    value: Decimal
    cycle: SubscriptionCycle
    status: SubscriptionStatus
    billing_type: BillingType
    next_due_date: date
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class AsaasSubscriptionUpdate(BaseModel):
    """Modelo para atualizar assinatura."""
    value: Optional[Decimal] = None
    next_due_date: Optional[date] = None
    cycle: Optional[SubscriptionCycle] = None
    billing_type: Optional[BillingType] = None
    description: Optional[str] = None


# ============================================================================
# WEBHOOK MODELS
# ============================================================================

class AsaasWebhookEvent(BaseModel):
    """Modelo de evento de webhook do Asaas."""
    event: str
    payment: Optional[dict] = None
    subscription: Optional[dict] = None


# ============================================================================
# DASHBOARD MODELS
# ============================================================================

class AsaasDashboardMetrics(BaseModel):
    """Modelo de métricas do dashboard."""
    mrr: Decimal = Decimal("0")
    total_customers: int = 0
    active_subscriptions: int = 0
    pending_payments: int = 0
    overdue_payments: int = 0
    received_this_month: Decimal = Decimal("0")
    churn_rate: float = 0.0


class AsaasPaymentStats(BaseModel):
    """Estatísticas de pagamentos."""
    total: int = 0
    pending: int = 0
    received: int = 0
    overdue: int = 0
    refunded: int = 0
    total_value: Decimal = Decimal("0")
    received_value: Decimal = Decimal("0")
    pending_value: Decimal = Decimal("0")


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