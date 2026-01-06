# ============================================================================
# ASAAS PROXY SERVER
# Servidor proxy para a API do Asaas (resolve problema de CORS)
# ============================================================================

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dotenv import load_dotenv
import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

load_dotenv()
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

ASAAS_API_KEY = os.getenv("ASAAS_API_KEY", "")
ASAAS_SANDBOX = os.getenv("ASAAS_SANDBOX", "true").lower() == "true"
ASAAS_BASE_URL = "https://api-sandbox.asaas.com/v3" if ASAAS_SANDBOX else "https://api.asaas.com/v3"

# Router FastAPI - Rota principal com /asaas
asaas_router = APIRouter(prefix="/api/v1/asaas", tags=["Asaas Proxy"])

# Router de compatibilidade - Sem prefixo /asaas para frontend legado
asaas_compat_router = APIRouter(prefix="/api/v1", tags=["Asaas Compat"])


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class CustomerCreate(BaseModel):
    name: str
    cpf_cnpj: str = Field(alias="cpfCnpj")
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = Field(None, alias="mobilePhone")
    address: Optional[str] = None
    address_number: Optional[str] = Field(None, alias="addressNumber")
    complement: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = Field(None, alias="postalCode")
    external_reference: Optional[str] = Field(None, alias="externalReference")
    notification_disabled: Optional[bool] = Field(None, alias="notificationDisabled")
    additional_emails: Optional[str] = Field(None, alias="additionalEmails")
    municipal_inscription: Optional[str] = Field(None, alias="municipalInscription")
    state_inscription: Optional[str] = Field(None, alias="stateInscription")
    observations: Optional[str] = None
    group_name: Optional[str] = Field(None, alias="groupName")
    company: Optional[str] = None

    class Config:
        populate_by_name = True


class PaymentCreate(BaseModel):
    customer_id: Optional[str] = Field(None, alias="customer")
    billing_type: Optional[str] = Field(None, alias="billingType")
    value: float
    due_date: Optional[str] = Field(None, alias="dueDate")
    description: Optional[str] = None
    external_reference: Optional[str] = Field(None, alias="externalReference")
    installment_count: Optional[int] = Field(None, alias="installmentCount")
    installment_value: Optional[float] = Field(None, alias="installmentValue")
    discount: Optional[Dict] = None
    interest: Optional[Dict] = None
    fine: Optional[Dict] = None
    postal_service: Optional[bool] = Field(None, alias="postalService")

    class Config:
        populate_by_name = True


class SubscriptionCreate(BaseModel):
    customer_id: Optional[str] = Field(None, alias="customer")
    billing_type: Optional[str] = Field(None, alias="billingType")
    value: float
    next_due_date: Optional[str] = Field(None, alias="nextDueDate")
    description: Optional[str] = None
    cycle: str = "MONTHLY"
    max_payments: Optional[int] = Field(None, alias="maxPayments")
    external_reference: Optional[str] = Field(None, alias="externalReference")
    discount: Optional[Dict] = None
    interest: Optional[Dict] = None
    fine: Optional[Dict] = None

    class Config:
        populate_by_name = True


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_asaas_headers() -> Dict[str, str]:
    """Retorna headers para requisições ao Asaas."""
    return {
        "Content-Type": "application/json",
        "User-Agent": "ecosys-dash-hub",
        "access_token": ASAAS_API_KEY,
    }


async def asaas_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict] = None,
    params: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Faz requisição para a API do Asaas.
    
    Args:
        endpoint: Endpoint da API (ex: /customers)
        method: Método HTTP (GET, POST, PUT, DELETE)
        data: Dados para enviar no body (POST/PUT)
        params: Query parameters (GET)
    
    Returns:
        Dict com data, error e status
    """
    url = f"{ASAAS_BASE_URL}{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=get_asaas_headers(), params=params)
            elif method == "POST":
                response = await client.post(url, headers=get_asaas_headers(), json=data)
            elif method == "PUT":
                response = await client.put(url, headers=get_asaas_headers(), json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=get_asaas_headers())
            else:
                return {"error": {"message": f"Método não suportado: {method}"}, "status": 400}
            
            # Tentar fazer parse do JSON, se falhar retorna erro vazio
            try:
                response_data = response.json()
            except Exception as json_error:
                logger.error(f"Erro ao fazer parse do JSON da resposta: {json_error}")
                response_data = {"message": "Resposta vazia ou inválida do servidor"}
            
            if response.status_code >= 400:
                logger.error(f"Erro Asaas [{response.status_code}]: {response_data}")
                return {"error": response_data, "status": response.status_code}
            
            return {"data": response_data, "status": response.status_code}
            
    except httpx.TimeoutException:
        logger.error(f"Timeout ao chamar Asaas: {endpoint}")
        return {"error": {"message": "Timeout na requisição"}, "status": 504}
    except Exception as e:
        logger.error(f"Erro ao chamar Asaas: {str(e)}")
        return {"error": {"message": str(e)}, "status": 500}


def sanitize_payment_dates(payment: Dict) -> Dict:
    """Sanitiza datas em um pagamento para evitar erros no frontend."""
    date_fields = [
        'dateCreated', 'dueDate', 'paymentDate', 'clientPaymentDate', 'estimatedCreditDate'
    ]
    
    sanitized = payment.copy()
    for field in date_fields:
        if field in sanitized and (sanitized[field] is None or sanitized[field] == 'null'):
            sanitized[field] = None
        elif field in sanitized and isinstance(sanitized[field], str):
            # Validar formato básico YYYY-MM-DD
            if not sanitized[field] or len(sanitized[field]) < 10:
                sanitized[field] = None
    
    return sanitized


def sanitize_subscription_dates(subscription: Dict) -> Dict:
    """Sanitiza datas em uma assinatura para evitar erros no frontend."""
    date_fields = [
        'dateCreated', 'nextDueDate'
    ]
    
    sanitized = subscription.copy()
    for field in date_fields:
        if field in sanitized and (sanitized[field] is None or sanitized[field] == 'null'):
            sanitized[field] = None
        elif field in sanitized and isinstance(sanitized[field], str):
            # Validar formato básico YYYY-MM-DD
            if not sanitized[field] or len(sanitized[field]) < 10:
                sanitized[field] = None
    
    return sanitized


def format_list_response(data: Dict, offset: int = 0, limit: int = 10, sanitize_dates: bool = False, data_type: str = "payments") -> Dict:
    """Formata resposta de listagem."""
    items = data.get("data", [])
    if sanitize_dates:
        if data_type == "payments":
            items = [sanitize_payment_dates(item) for item in items]
        elif data_type == "subscriptions":
            items = [sanitize_subscription_dates(item) for item in items]
    
    return {
        "data": items,
        "hasMore": data.get("hasMore", False),
        "totalCount": data.get("totalCount", 0),
        "offset": offset,
        "limit": limit,
    }


# ============================================================================
# ROTAS - CLIENTES
# ============================================================================

@asaas_router.get("/customers")
async def list_customers(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    name: Optional[str] = None,
    email: Optional[str] = None,
    cpfCnpj: Optional[str] = None,
    groupName: Optional[str] = None,
    externalReference: Optional[str] = None,
):
    """Lista clientes do Asaas."""
    params = {"offset": offset, "limit": limit}
    if name:
        params["name"] = name
    if email:
        params["email"] = email
    if cpfCnpj:
        params["cpfCnpj"] = cpfCnpj
    if groupName:
        params["groupName"] = groupName
    if externalReference:
        params["externalReference"] = externalReference
    
    result = await asaas_request("/customers", params=params)
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return format_list_response(result["data"], offset, limit)


@asaas_router.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    """Busca cliente por ID."""
    result = await asaas_request(f"/customers/{customer_id}")
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


@asaas_router.post("/customers")
async def create_customer(customer: CustomerCreate):
    """Cria novo cliente no Asaas."""
    data = customer.model_dump(exclude_none=True, by_alias=True)
    result = await asaas_request("/customers", method="POST", data=data)
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


@asaas_router.put("/customers/{customer_id}")
async def update_customer(customer_id: str, request: Request):
    """Atualiza cliente existente."""
    data = await request.json()
    result = await asaas_request(f"/customers/{customer_id}", method="PUT", data=data)
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


@asaas_router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str):
    """Remove cliente."""
    result = await asaas_request(f"/customers/{customer_id}", method="DELETE")
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


@asaas_router.get("/customers/{customer_id}/payments")
async def get_customer_payments(customer_id: str):
    """Lista pagamentos de um cliente."""
    result = await asaas_request(f"/customers/{customer_id}/payments")
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return format_list_response(result["data"], 0, 100)


@asaas_router.get("/customers/{customer_id}/subscriptions")
async def get_customer_subscriptions(customer_id: str):
    """Lista assinaturas de um cliente."""
    result = await asaas_request(f"/customers/{customer_id}/subscriptions")
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return format_list_response(result["data"], 0, 100)


# ============================================================================
# ROTAS - COBRANÇAS (PAYMENTS)
# ============================================================================

@asaas_router.get("/payments")
async def list_payments(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    customer: Optional[str] = None,
    subscription: Optional[str] = None,
    installment: Optional[str] = None,
    status: Optional[str] = None,
    billingType: Optional[str] = None,
    externalReference: Optional[str] = None,
    dateCreated_ge: Optional[str] = None,
    dateCreated_le: Optional[str] = None,
    dueDate_ge: Optional[str] = None,
    dueDate_le: Optional[str] = None,
):
    """Lista cobranças do Asaas."""
    params = {"offset": offset, "limit": limit}
    if customer:
        params["customer"] = customer
    if subscription:
        params["subscription"] = subscription
    if installment:
        params["installment"] = installment
    if status:
        params["status"] = status
    if billingType:
        params["billingType"] = billingType
    if externalReference:
        params["externalReference"] = externalReference
    if dateCreated_ge:
        params["dateCreated[ge]"] = dateCreated_ge
    if dateCreated_le:
        params["dateCreated[le]"] = dateCreated_le
    if dueDate_ge:
        params["dueDate[ge]"] = dueDate_ge
    if dueDate_le:
        params["dueDate[le]"] = dueDate_le
    
    result = await asaas_request("/payments", params=params)
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return format_list_response(result["data"], offset, limit, sanitize_dates=True)


@asaas_router.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    """Busca cobrança por ID."""
    result = await asaas_request(f"/payments/{payment_id}")
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return sanitize_payment_dates(result["data"])


@asaas_router.post("/payments")
async def create_payment(payment: PaymentCreate):
    """Cria nova cobrança no Asaas."""
    # Mapear campos do frontend para API Asaas
    api_data = {
        "customer": payment.customer_id,
        "billingType": payment.billing_type,
        "value": payment.value,
        "dueDate": payment.due_date,
        "description": payment.description,
        "externalReference": payment.external_reference,
        "installmentCount": payment.installment_count,
        "installmentValue": payment.installment_value,
        "discount": payment.discount,
        "interest": payment.interest,
        "fine": payment.fine,
        "postalService": payment.postal_service,
    }
    
    # Remover campos None
    api_data = {k: v for k, v in api_data.items() if v is not None}
    
    result = await asaas_request("/payments", method="POST", data=api_data)
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


@asaas_router.put("/payments/{payment_id}")
async def update_payment(payment_id: str, request: Request):
    """Atualiza cobrança existente."""
    data = await request.json()
    result = await asaas_request(f"/payments/{payment_id}", method="PUT", data=data)
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


@asaas_router.delete("/payments/{payment_id}")
async def delete_payment(payment_id: str):
    """Remove cobrança."""
    result = await asaas_request(f"/payments/{payment_id}", method="DELETE")
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


@asaas_router.get("/payments/{payment_id}/link")
async def get_payment_link(payment_id: str):
    """Retorna URLs de pagamento (boleto, pix, etc)."""
    result = await asaas_request(f"/payments/{payment_id}")
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    data = result["data"]
    return {
        "id": payment_id,
        "invoice_url": data.get("invoiceUrl"),
        "bank_slip_url": data.get("bankSlipUrl"),
        "pix_qr_code_url": None,
        "pix_copy_paste": None,
    }


@asaas_router.get("/payments/{payment_id}/pixQrCode")
async def get_payment_pix_qrcode(payment_id: str):
    """Retorna QR Code Pix para pagamento."""
    result = await asaas_request(f"/payments/{payment_id}/pixQrCode")
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


@asaas_router.get("/payments/{payment_id}/identificationField")
async def get_payment_identification_field(payment_id: str):
    """Retorna linha digitável do boleto."""
    result = await asaas_request(f"/payments/{payment_id}/identificationField")
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


@asaas_router.post("/payments/{payment_id}/refund")
async def refund_payment(payment_id: str, request: Request):
    """Estorna cobrança."""
    try:
        data = await request.json()
    except:
        data = {}
    
    result = await asaas_request(f"/payments/{payment_id}/refund", method="POST", data=data)
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


# ============================================================================
# ROTAS - ASSINATURAS (SUBSCRIPTIONS)
# ============================================================================

@asaas_router.get("/subscriptions")
async def list_subscriptions(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    customer: Optional[str] = None,
    status: Optional[str] = None,
    billingType: Optional[str] = None,
    externalReference: Optional[str] = None,
):
    """Lista assinaturas do Asaas."""
    params = {"offset": offset, "limit": limit}
    if customer:
        params["customer"] = customer
    if status:
        params["status"] = status
    if billingType:
        params["billingType"] = billingType
    if externalReference:
        params["externalReference"] = externalReference
    
    result = await asaas_request("/subscriptions", params=params)
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return format_list_response(result["data"], offset, limit, sanitize_dates=True, data_type="subscriptions")


@asaas_router.get("/subscriptions/metrics")
async def get_subscriptions_metrics():
    """Retorna métricas de assinaturas."""
    import asyncio
    
    try:
        results = await asyncio.gather(
            asaas_request("/subscriptions", params={"status": "ACTIVE", "limit": 100}),
            asaas_request("/subscriptions", params={"status": "INACTIVE", "limit": 1}),
            asaas_request("/subscriptions", params={"status": "EXPIRED", "limit": 1}),
            return_exceptions=True
        )
        
        active, inactive, expired = results
        
        # Handle exceptions and errors in results
        if isinstance(active, Exception) or "error" in active:
            logger.warning(f"Erro ao buscar assinaturas ativas: {active}")
            active = {"data": {"data": [], "totalCount": 0}}
        if isinstance(inactive, Exception) or "error" in inactive:
            logger.warning(f"Erro ao buscar assinaturas inativas: {inactive}")
            inactive = {"data": {"data": [], "totalCount": 0}}
        if isinstance(expired, Exception) or "error" in expired:
            logger.warning(f"Erro ao buscar assinaturas expiradas: {expired}")
            expired = {"data": {"data": [], "totalCount": 0}}
        
        # Extract data safely
        active_data = active.get("data", {}).get("data", []) if isinstance(active, dict) and "data" in active else []
        total_mrr = sum(
            calculate_monthly_value(sub.get("value", 0), sub.get("cycle", "MONTHLY"))
            for sub in active_data
        )
        
        return {
            "total": (
                (active.get("data", {}).get("totalCount", 0) if isinstance(active, dict) and "data" in active else 0) +
                (inactive.get("data", {}).get("totalCount", 0) if isinstance(inactive, dict) and "data" in inactive else 0) +
                (expired.get("data", {}).get("totalCount", 0) if isinstance(expired, dict) and "data" in expired else 0)
            ),
            "active": active.get("data", {}).get("totalCount", 0) if isinstance(active, dict) and "data" in active else 0,
            "inactive": inactive.get("data", {}).get("totalCount", 0) if isinstance(inactive, dict) and "data" in inactive else 0,
            "expired": expired.get("data", {}).get("totalCount", 0) if isinstance(expired, dict) and "data" in expired else 0,
            "mrr": total_mrr,
        }
    except Exception as e:
        logger.error(f"Erro ao buscar métricas de assinaturas: {e}")
        return {
            "total": 0,
            "active": 0,
            "inactive": 0,
            "expired": 0,
            "mrr": 0,
            "error": str(e),
        }


@asaas_router.get("/subscriptions/{subscription_id}")
async def get_subscription(subscription_id: str):
    """Busca assinatura por ID."""
    result = await asaas_request(f"/subscriptions/{subscription_id}")
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return sanitize_subscription_dates(result["data"])


@asaas_router.post("/subscriptions")
async def create_subscription(subscription: SubscriptionCreate):
    """Cria nova assinatura no Asaas."""
    # Mapear campos do frontend para API Asaas
    api_data = {
        "customer": subscription.customer_id,
        "billingType": subscription.billing_type,
        "value": subscription.value,
        "nextDueDate": subscription.next_due_date,
        "description": subscription.description,
        "cycle": subscription.cycle,
        "maxPayments": subscription.max_payments,
        "externalReference": subscription.external_reference,
        "discount": subscription.discount,
        "interest": subscription.interest,
        "fine": subscription.fine,
    }
    
    # Remover campos None
    api_data = {k: v for k, v in api_data.items() if v is not None}
    
    result = await asaas_request("/subscriptions", method="POST", data=api_data)
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


@asaas_router.put("/subscriptions/{subscription_id}")
async def update_subscription(subscription_id: str, request: Request):
    """Atualiza assinatura existente."""
    data = await request.json()
    result = await asaas_request(f"/subscriptions/{subscription_id}", method="PUT", data=data)
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


@asaas_router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(subscription_id: str):
    """Remove assinatura."""
    result = await asaas_request(f"/subscriptions/{subscription_id}", method="DELETE")
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return result["data"]


@asaas_router.get("/subscriptions/{subscription_id}/payments")
async def get_subscription_payments(subscription_id: str):
    """Lista cobranças de uma assinatura."""
    result = await asaas_request(f"/subscriptions/{subscription_id}/payments")
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    return format_list_response(result["data"], 0, 100)


# ============================================================================
# ROTAS - DASHBOARD / MÉTRICAS
# ============================================================================

def calculate_monthly_value(value: float, cycle: str) -> float:
    """Calcula valor mensal baseado no ciclo."""
    cycle_multipliers = {
        "WEEKLY": 4,
        "BIWEEKLY": 2,
        "MONTHLY": 1,
        "QUARTERLY": 1/3,
        "SEMIANNUALLY": 1/6,
        "YEARLY": 1/12,
    }
    return value * cycle_multipliers.get(cycle, 1)


@asaas_router.get("/dashboard")
async def get_dashboard():
    """Retorna dashboard completo com métricas."""
    import asyncio
    
    # Buscar dados em paralelo
    results = await asyncio.gather(
        asaas_request("/subscriptions", params={"status": "ACTIVE", "limit": 100}),
        asaas_request("/subscriptions", params={"status": "INACTIVE", "limit": 100}),
        asaas_request("/payments", params={"status": "RECEIVED", "limit": 100}),
        asaas_request("/payments", params={"status": "PENDING", "limit": 100}),
        asaas_request("/payments", params={"status": "OVERDUE", "limit": 100}),
        return_exceptions=True
    )
    
    active_subs_result, inactive_subs_result, received_result, pending_result, overdue_result = results
    
    # Calcular MRR
    active_subscriptions = active_subs_result.get("data", {}).get("data", []) if isinstance(active_subs_result, dict) else []
    total_mrr = sum(
        calculate_monthly_value(sub.get("value", 0), sub.get("cycle", "MONTHLY"))
        for sub in active_subscriptions
    )
    
    # Calcular pagamentos
    received = received_result.get("data", {}).get("data", []) if isinstance(received_result, dict) else []
    pending = pending_result.get("data", {}).get("data", []) if isinstance(pending_result, dict) else []
    overdue = overdue_result.get("data", {}).get("data", []) if isinstance(overdue_result, dict) else []
    
    # Calcular churn
    inactive_count = inactive_subs_result.get("data", {}).get("totalCount", 0) if isinstance(inactive_subs_result, dict) else 0
    active_count = active_subs_result.get("data", {}).get("totalCount", 0) if isinstance(active_subs_result, dict) else 0
    total_subs = active_count + inactive_count
    churn_rate = (inactive_count / total_subs * 100) if total_subs > 0 else 0
    
    # Agrupar inadimplentes
    overdue_by_customer = {}
    for p in overdue:
        cid = p.get("customer")
        if cid not in overdue_by_customer:
            overdue_by_customer[cid] = {
                "customer_id": cid,
                "customer_name": p.get("customerName", cid),
                "total_overdue": 0,
                "overdue_payments": 0,
                "oldest_due_date": p.get("dueDate"),
            }
        overdue_by_customer[cid]["total_overdue"] += p.get("value", 0)
        overdue_by_customer[cid]["overdue_payments"] += 1
        if p.get("dueDate", "") < overdue_by_customer[cid]["oldest_due_date"]:
            overdue_by_customer[cid]["oldest_due_date"] = p.get("dueDate")
    
    return {
        "mrr": {
            "current": total_mrr,
            "active_subscriptions": active_count,
            "avg_ticket": total_mrr / active_count if active_count > 0 else 0,
        },
        "payments": {
            "total_count": len(received) + len(pending) + len(overdue),
            "received_count": received_result.get("data", {}).get("totalCount", len(received)) if isinstance(received_result, dict) else 0,
            "pending_count": pending_result.get("data", {}).get("totalCount", len(pending)) if isinstance(pending_result, dict) else 0,
            "overdue_count": overdue_result.get("data", {}).get("totalCount", len(overdue)) if isinstance(overdue_result, dict) else 0,
            "total_value": sum(p.get("value", 0) for p in received + pending + overdue),
            "received_value": sum(p.get("value", 0) for p in received),
            "pending_value": sum(p.get("value", 0) for p in pending),
            "overdue_value": sum(p.get("value", 0) for p in overdue),
        },
        "overdue": sorted(overdue_by_customer.values(), key=lambda x: x["total_overdue"], reverse=True),
        "churn": {
            "churn_rate": churn_rate,
            "canceled_subscriptions": inactive_count,
            "active_subscriptions": active_count,
        },
    }


@asaas_router.get("/dashboard/mrr")
async def get_dashboard_mrr():
    """Retorna MRR (Monthly Recurring Revenue)."""
    result = await asaas_request("/subscriptions", params={"status": "ACTIVE", "limit": 100})
    
    if "error" in result:
        logger.warning(f"Erro ao buscar MRR: {result['error']}")
        return {
            "current": 0,
            "active_subscriptions": 0,
            "avg_ticket": 0,
        }
    
    subscriptions = result.get("data", {}).get("data", []) if "data" in result else []
    total_mrr = sum(
        calculate_monthly_value(sub.get("value", 0), sub.get("cycle", "MONTHLY"))
        for sub in subscriptions
    )
    
    return {
        "current": total_mrr,
        "active_subscriptions": len(subscriptions),
        "avg_ticket": total_mrr / len(subscriptions) if subscriptions else 0,
    }


@asaas_router.get("/dashboard/payments")
async def get_dashboard_payments():
    """Retorna resumo de pagamentos."""
    import asyncio
    
    results = await asyncio.gather(
        asaas_request("/payments", params={"status": "RECEIVED", "limit": 100}),
        asaas_request("/payments", params={"status": "PENDING", "limit": 100}),
        asaas_request("/payments", params={"status": "OVERDUE", "limit": 100}),
        return_exceptions=True
    )
    
    received, pending, overdue = results
    
    # Handle errors
    if isinstance(received, Exception) or "error" in received:
        received = {"data": {"data": [], "totalCount": 0}}
    if isinstance(pending, Exception) or "error" in pending:
        pending = {"data": {"data": [], "totalCount": 0}}
    if isinstance(overdue, Exception) or "error" in overdue:
        overdue = {"data": {"data": [], "totalCount": 0}}
    
    received_data = received.get("data", {}).get("data", []) if isinstance(received, dict) and "data" in received else []
    pending_data = pending.get("data", {}).get("data", []) if isinstance(pending, dict) and "data" in pending else []
    overdue_data = overdue.get("data", {}).get("data", []) if isinstance(overdue, dict) and "data" in overdue else []
    
    return {
        "total_count": len(received_data) + len(pending_data) + len(overdue_data),
        "received_count": received.get("data", {}).get("totalCount", len(received_data)) if isinstance(received, dict) and "data" in received else 0,
        "pending_count": pending.get("data", {}).get("totalCount", len(pending_data)) if isinstance(pending, dict) and "data" in pending else 0,
        "overdue_count": overdue.get("data", {}).get("totalCount", len(overdue_data)) if isinstance(overdue, dict) and "data" in overdue else 0,
        "total_value": sum(p.get("value", 0) for p in received_data + pending_data + overdue_data),
        "received_value": sum(p.get("value", 0) for p in received_data),
        "pending_value": sum(p.get("value", 0) for p in pending_data),
        "overdue_value": sum(p.get("value", 0) for p in overdue_data),
    }


@asaas_router.get("/dashboard/overdue")
async def get_dashboard_overdue():
    """Retorna lista de inadimplentes."""
    result = await asaas_request("/payments", params={"status": "OVERDUE", "limit": 100})
    
    if "error" in result:
        logger.warning(f"Erro ao buscar inadimplentes: {result['error']}")
        return []
    
    payments = result.get("data", {}).get("data", []) if "data" in result else []
    customer_map = {}
    
    for p in payments:
        cid = p.get("customer")
        if cid not in customer_map:
            customer_map[cid] = {
                "customer_id": cid,
                "customer_name": p.get("customerName", cid),
                "total_overdue": 0,
                "overdue_payments": 0,
                "oldest_due_date": p.get("dueDate"),
            }
        customer_map[cid]["total_overdue"] += p.get("value", 0)
        customer_map[cid]["overdue_payments"] += 1
        if p.get("dueDate", "") < customer_map[cid]["oldest_due_date"]:
            customer_map[cid]["oldest_due_date"] = p.get("dueDate")
    
    return sorted(customer_map.values(), key=lambda x: x["total_overdue"], reverse=True)


@asaas_router.get("/dashboard/churn")
async def get_dashboard_churn():
    """Retorna taxa de churn."""
    import asyncio
    
    results = await asyncio.gather(
        asaas_request("/subscriptions", params={"status": "ACTIVE", "limit": 1}),
        asaas_request("/subscriptions", params={"status": "INACTIVE", "limit": 1}),
        return_exceptions=True
    )
    
    active, inactive = results
    
    # Handle errors
    if isinstance(active, Exception) or "error" in active:
        active = {"data": {"totalCount": 0}}
    if isinstance(inactive, Exception) or "error" in inactive:
        inactive = {"data": {"totalCount": 0}}
    
    active_count = active.get("data", {}).get("totalCount", 0) if isinstance(active, dict) and "data" in active else 0
    inactive_count = inactive.get("data", {}).get("totalCount", 0) if isinstance(inactive, dict) and "data" in inactive else 0
    total = active_count + inactive_count
    
    return {
        "churn_rate": (inactive_count / total * 100) if total > 0 else 0,
        "canceled_subscriptions": inactive_count,
        "active_subscriptions": active_count,
    }


@asaas_router.get("/dashboard/revenue")
async def get_dashboard_revenue():
    """Retorna receita por status."""
    import asyncio
    
    results = await asyncio.gather(
        asaas_request("/payments", params={"status": "RECEIVED", "limit": 100}),
        asaas_request("/payments", params={"status": "PENDING", "limit": 100}),
        asaas_request("/payments", params={"status": "OVERDUE", "limit": 100}),
        return_exceptions=True
    )
    
    received, pending, overdue = results
    
    # Handle errors
    if isinstance(received, Exception) or "error" in received:
        received = {"data": {"data": []}}
    if isinstance(pending, Exception) or "error" in pending:
        pending = {"data": {"data": []}}
    if isinstance(overdue, Exception) or "error" in overdue:
        overdue = {"data": {"data": []}}
    
    received_data = received.get("data", {}).get("data", []) if isinstance(received, dict) and "data" in received else []
    pending_data = pending.get("data", {}).get("data", []) if isinstance(pending, dict) and "data" in pending else []
    overdue_data = overdue.get("data", {}).get("data", []) if isinstance(overdue, dict) and "data" in overdue else []
    
    return {
        "total": sum(p.get("value", 0) for p in received_data + pending_data + overdue_data),
        "received": sum(p.get("value", 0) for p in received_data),
        "pending": sum(p.get("value", 0) for p in pending_data),
        "overdue": sum(p.get("value", 0) for p in overdue_data),
    }


@asaas_router.get("/customers/stats")
async def get_customers_stats():
    """Retorna estatísticas de clientes."""
    import asyncio
    
    results = await asyncio.gather(
        asaas_request("/customers", params={"limit": 100}),
        asaas_request("/payments", params={"status": "OVERDUE", "limit": 100}),
        return_exceptions=True
    )
    
    customers, overdue = results
    
    # Handle exceptions in results
    if isinstance(customers, Exception):
        customers = {"data": {"data": [], "totalCount": 0}}
    if isinstance(overdue, Exception):
        overdue = {"data": {"data": []}}
    
    customers_data = customers.get("data", {}).get("data", []) if isinstance(customers, dict) else []
    overdue_data = overdue.get("data", {}).get("data", []) if isinstance(overdue, dict) else []
    overdue_customer_ids = set(p.get("customer") for p in overdue_data)
    
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    
    new_customers = 0
    for c in customers_data:
        date_created = c.get("dateCreated")
        if date_created:
            try:
                created = datetime.fromisoformat(date_created.replace("Z", "+00:00"))
                if created.replace(tzinfo=None) >= thirty_days_ago:
                    new_customers += 1
            except:
                pass
    
    return {
        "total_customers": customers.get("data", {}).get("totalCount", len(customers_data)) if isinstance(customers, dict) else 0,
        "active_customers": len([c for c in customers_data if not c.get("deleted")]),
        "inactive_customers": len([c for c in customers_data if c.get("deleted")]),
        "new_last_30_days": new_customers,
        "overdue_customers": len(overdue_customer_ids),
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@asaas_router.get("/health")
async def asaas_health_check():
    """Verifica status da conexão com Asaas."""
    if not ASAAS_API_KEY:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "ASAAS_API_KEY não configurada",
                "environment": "sandbox" if ASAAS_SANDBOX else "production",
                "asaas_url": ASAAS_BASE_URL,
            }
        )
    
    # Testar conexão
    result = await asaas_request("/customers", params={"limit": 1})
    
    if "error" in result:
        return JSONResponse(
            status_code=result["status"],
            content={
                "status": "error",
                "message": "Falha na conexão com Asaas",
                "error": result["error"],
                "environment": "sandbox" if ASAAS_SANDBOX else "production",
                "asaas_url": ASAAS_BASE_URL,
            }
        )
    
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "environment": "sandbox" if ASAAS_SANDBOX else "production",
        "asaas_url": ASAAS_BASE_URL,
        "api_key_configured": bool(ASAAS_API_KEY),
        "api_key_preview": f"{ASAAS_API_KEY[:15]}..." if ASAAS_API_KEY else None,
    }


# ============================================================================
# ROTAS DE COMPATIBILIDADE (sem prefixo /asaas)
# Para suportar chamadas do frontend que não usam /asaas
# ============================================================================

@asaas_compat_router.get("/customers/{customer_id}")
async def compat_get_customer(customer_id: str):
    """Busca cliente por ID (compatibilidade)."""
    return await get_customer(customer_id)


@asaas_compat_router.get("/customers/{customer_id}/payments")
async def compat_get_customer_payments(customer_id: str):
    """Lista pagamentos de um cliente (compatibilidade)."""
    return await get_customer_payments(customer_id)


@asaas_compat_router.get("/customers/{customer_id}/subscriptions")
async def compat_get_customer_subscriptions(customer_id: str):
    """Lista assinaturas de um cliente (compatibilidade)."""
    return await get_customer_subscriptions(customer_id)


@asaas_compat_router.get("/subscriptions/metrics")
async def compat_get_subscriptions_metrics():
    """Retorna métricas de assinaturas (compatibilidade)."""
    return await get_subscriptions_metrics()


@asaas_compat_router.get("/customers/stats")
async def compat_get_customers_stats():
    """Retorna estatísticas de clientes (compatibilidade)."""
    return await get_customers_stats()


@asaas_compat_router.get("/dashboard")
async def compat_get_dashboard():
    """Retorna dashboard completo (compatibilidade)."""
    return await get_dashboard()


@asaas_compat_router.get("/dashboard/mrr")
async def compat_get_dashboard_mrr():
    """Retorna MRR (compatibilidade)."""
    return await get_dashboard_mrr()


@asaas_compat_router.get("/dashboard/payments")
async def compat_get_dashboard_payments():
    """Retorna resumo de pagamentos (compatibilidade)."""
    return await get_dashboard_payments()


@asaas_compat_router.get("/dashboard/overdue")
async def compat_get_dashboard_overdue():
    """Retorna lista de inadimplentes (compatibilidade)."""
    return await get_dashboard_overdue()


@asaas_compat_router.get("/dashboard/churn")
async def compat_get_dashboard_churn():
    """Retorna taxa de churn (compatibilidade)."""
    return await get_dashboard_churn()


@asaas_compat_router.get("/dashboard/revenue")
async def compat_get_dashboard_revenue():
    """Retorna receita por status (compatibilidade)."""
    return await get_dashboard_revenue()


@asaas_compat_router.get("/payments")
async def compat_list_payments(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    customer: Optional[str] = None,
    status: Optional[str] = None,
):
    """Lista cobranças (compatibilidade)."""
    return await list_payments(offset=offset, limit=limit, customer=customer, status=status)


@asaas_compat_router.get("/payments/{payment_id}")
async def compat_get_payment(payment_id: str):
    """Busca cobrança por ID (compatibilidade)."""
    return await get_payment(payment_id)


@asaas_compat_router.get("/subscriptions")
async def compat_list_subscriptions(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    customer: Optional[str] = None,
    status: Optional[str] = None,
):
    """Lista assinaturas (compatibilidade)."""
    return await list_subscriptions(offset=offset, limit=limit, customer=customer, status=status)


@asaas_compat_router.get("/subscriptions/{subscription_id}")
async def compat_get_subscription(subscription_id: str):
    """Busca assinatura por ID (compatibilidade)."""
    return await get_subscription(subscription_id)
