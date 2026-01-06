"""
Endpoints de Pagamentos com Asaas.

Módulo que fornece endpoints para:
- Gestão de Clientes (sync com Asaas)
- Cobranças/Pagamentos
- Assinaturas
- Produtos
- Dashboard/Métricas
"""

import logging
import json
import os
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from ..lib.db_connection import get_conn
from ..lib.asaas_client import (
    asaas_client,
    sync_customer_to_asaas,
    create_simple_payment,
    create_simple_subscription
)
from ..lib.models import (
    PaymentStatus,
    BillingType,
    SubscriptionCycle,
    SubscriptionStatus,
    AsaasCustomerCreate,
    AsaasCustomerResponse,
    AsaasProductCreate,
    AsaasProductResponse,
    AsaasPaymentCreate,
    AsaasPaymentResponse,
    AsaasPaymentUpdate,
    AsaasSubscriptionCreate,
    AsaasSubscriptionResponse,
    AsaasSubscriptionUpdate,
    AsaasDashboardMetrics,
    AsaasPaymentStats,
    AsaasWebhookEvent,
    PaginatedResponse
)
from ..lib.asaas_queries import (
    INSERT_ASAAS_CUSTOMER,
    SELECT_ASAAS_CUSTOMER_BY_ID,
    SELECT_ASAAS_CUSTOMER_BY_ASAAS_ID,
    SELECT_ASAAS_CUSTOMER_BY_CPF_CNPJ,
    SELECT_ALL_ASAAS_CUSTOMERS,
    COUNT_ASAAS_CUSTOMERS,
    UPDATE_ASAAS_CUSTOMER,
    DELETE_ASAAS_CUSTOMER,
    INSERT_ASAAS_PRODUCT,
    SELECT_ASAAS_PRODUCT_BY_ID,
    SELECT_ALL_ASAAS_PRODUCTS,
    SELECT_ACTIVE_ASAAS_PRODUCTS,
    COUNT_ASAAS_PRODUCTS,
    UPDATE_ASAAS_PRODUCT,
    DELETE_ASAAS_PRODUCT,
    INSERT_ASAAS_PAYMENT,
    SELECT_ASAAS_PAYMENT_BY_ID,
    SELECT_ASAAS_PAYMENT_BY_ASAAS_ID,
    SELECT_ALL_ASAAS_PAYMENTS,
    SELECT_PAYMENTS_BY_CUSTOMER,
    COUNT_ASAAS_PAYMENTS,
    UPDATE_ASAAS_PAYMENT_STATUS,
    DELETE_ASAAS_PAYMENT,
    INSERT_ASAAS_SUBSCRIPTION,
    SELECT_ASAAS_SUBSCRIPTION_BY_ID,
    SELECT_ASAAS_SUBSCRIPTION_BY_ASAAS_ID,
    SELECT_ALL_ASAAS_SUBSCRIPTIONS,
    SELECT_SUBSCRIPTIONS_BY_CUSTOMER,
    SELECT_ACTIVE_SUBSCRIPTIONS,
    COUNT_ASAAS_SUBSCRIPTIONS,
    UPDATE_ASAAS_SUBSCRIPTION,
    DELETE_ASAAS_SUBSCRIPTION,
    SELECT_MRR,
    SELECT_PAYMENT_STATS,
    SELECT_OVERDUE_CUSTOMERS,
    SELECT_REVENUE_BY_PERIOD,
    SELECT_SUBSCRIPTION_METRICS,
    SELECT_CUSTOMER_STATS,
    SELECT_OVERALL_CHURN,
    SELECT_CHURN_RATE,
    INSERT_OR_UPDATE_ASAAS_PAYMENT,
    INSERT_OR_UPDATE_ASAAS_SUBSCRIPTION
)

logger = logging.getLogger(__name__)

# ============================================================================
# AUTENTICAÇÃO
# ============================================================================

security = HTTPBasic()

@lru_cache(maxsize=1)
def get_users() -> Dict[str, str]:
    """Carrega usuários do .env com cache"""
    users = {}
    users_env = os.getenv("BASIC_AUTH_USERS")
    if users_env:
        for pair in users_env.split(","):
            if ":" in pair:
                user, pwd = pair.split(":", 1)
                users[user.strip()] = pwd.strip()
    return users

def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Valida credenciais Basic Auth"""
    users = get_users()
    password = users.get(credentials.username)
    
    if not password or not secrets.compare_digest(credentials.password, password):
        raise HTTPException(
            status_code=401, 
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"}
        )
    return credentials

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix="/api/v1/asaas",
    tags=["Asaas Payments"],
    dependencies=[Depends(verify_basic_auth)]
)


# ============================================================================
# HELPERS
# ============================================================================

def execute_query(query: str, params: dict, fetch_one: bool = False) -> Any:
    """Executa query e retorna resultado."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                conn.commit()
                if "RETURNING" in query.upper():
                    return cur.fetchone() if fetch_one else cur.fetchall()
                return None
            return cur.fetchone() if fetch_one else cur.fetchall()
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro na query: {e}")
        raise
    finally:
        conn.close()


def row_to_dict(row, columns: List[str]) -> dict:
    """Converte row do banco para dict."""
    if row is None:
        return None
    return dict(zip(columns, row))


def serialize_value(value: Any) -> Any:
    """Serializa valores para JSON."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return value
    return value


def serialize_row(row_dict: dict) -> dict:
    """Serializa todos os valores de um dict."""
    return {k: serialize_value(v) for k, v in row_dict.items()}


@router.get("/test-connection")
async def test_asaas_connection():
    """Testa a conexão com a API do Asaas."""
    try:
        success = await asaas_client.test_connection()
        if success:
            return {"status": "success", "message": "Conexão com Asaas estabelecida"}
        else:
            return {"status": "error", "message": "Falha na conexão com Asaas"}
    except Exception as e:
        logger.error(f"Erro no teste de conexão: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-cpf-cnpj")
async def validate_cpf_cnpj_endpoint(cpf_cnpj: str):
    """Valida CPF ou CNPJ."""
    try:
        from ..lib.models import validate_cpf_cnpj
        cleaned = validate_cpf_cnpj(cpf_cnpj)
        doc_type = "CPF" if len(cleaned) == 11 else "CNPJ"
        return {
            "valid": True,
            "type": doc_type,
            "cleaned": cleaned,
            "original": cpf_cnpj
        }
    except ValueError as e:
        return {
            "valid": False,
            "error": str(e),
            "original": cpf_cnpj
        }

CUSTOMER_COLUMNS = [
    "id", "asaas_id", "name", "email", "cpf_cnpj", 
    "phone", "address", "active", "created_at", "updated_at"
]


@router.get("/customers/stats")
async def get_customer_stats():
    """Obtém estatísticas de clientes."""
    try:
        result = execute_query(SELECT_CUSTOMER_STATS, {}, fetch_one=True)
        
        if result:
            return {
                "total_customers": result[0] or 0,
                "active_customers": result[1] or 0,
                "inactive_customers": result[2] or 0,
                "new_last_30_days": result[3] or 0,
                "overdue_customers": result[4] or 0
            }
        
        return {
            "total_customers": 0,
            "active_customers": 0,
            "inactive_customers": 0,
            "new_last_30_days": 0,
            "overdue_customers": 0
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas de clientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers", response_model=PaginatedResponse)
async def list_customers(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    active: Optional[bool] = None
):
    """Lista clientes sincronizados com Asaas."""
    try:
        params = {"offset": offset, "limit": limit, "active": active}
        
        rows = execute_query(SELECT_ALL_ASAAS_CUSTOMERS, params)
        count_result = execute_query(COUNT_ASAAS_CUSTOMERS, params, fetch_one=True)
        
        data = [serialize_row(row_to_dict(row, CUSTOMER_COLUMNS)) for row in rows]
        total = count_result[0] if count_result else 0
        
        return {
            "data": data,
            "total_count": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total
        }
    except Exception as e:
        logger.error(f"Erro ao listar clientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/customers")
async def create_customer(customer: AsaasCustomerCreate):
    """
    Cria um cliente no Asaas e salva localmente.
    Se já existe (por CPF/CNPJ), retorna os dados existentes.
    """
    try:
        # Verificar se já existe localmente
        existing = execute_query(
            SELECT_ASAAS_CUSTOMER_BY_CPF_CNPJ, 
            {"cpf_cnpj": customer.cpf_cnpj}, 
            fetch_one=True
        )
        if existing:
            return serialize_row(row_to_dict(existing, CUSTOMER_COLUMNS))
        
        # Criar no Asaas
        asaas_response = await sync_customer_to_asaas(
            name=customer.name,
            cpf_cnpj=customer.cpf_cnpj,
            email=customer.email,
            phone=customer.phone or customer.mobile_phone,
            external_reference=customer.external_reference
        )
        
        # Salvar localmente
        address_json = json.dumps(customer.address.dict()) if customer.address else None
        
        params = {
            "asaas_id": asaas_response.get("id"),
            "name": customer.name,
            "email": customer.email,
            "cpf_cnpj": customer.cpf_cnpj,
            "phone": customer.phone or customer.mobile_phone,
            "address": address_json,
            "active": True
        }
        
        result = execute_query(INSERT_ASAAS_CUSTOMER, params, fetch_one=True)
        
        return serialize_row(row_to_dict(result, CUSTOMER_COLUMNS))
        
    except Exception as e:
        logger.error(f"Erro ao criar cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    """Obtém detalhes de um cliente."""
    try:
        row = execute_query(
            SELECT_ASAAS_CUSTOMER_BY_ID, 
            {"id": customer_id}, 
            fetch_one=True
        )
        if not row:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        return serialize_row(row_to_dict(row, CUSTOMER_COLUMNS))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/customers/{customer_id}")
async def update_customer(customer_id: str, data: dict):
    """Atualiza um cliente."""
    try:
        # Buscar cliente local
        existing = execute_query(
            SELECT_ASAAS_CUSTOMER_BY_ID, 
            {"id": customer_id}, 
            fetch_one=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        existing_dict = row_to_dict(existing, CUSTOMER_COLUMNS)
        asaas_id = existing_dict.get("asaas_id")
        
        # Atualizar no Asaas
        if asaas_id:
            asaas_data = {}
            if "name" in data:
                asaas_data["name"] = data["name"]
            if "email" in data:
                asaas_data["email"] = data["email"]
            if "phone" in data:
                asaas_data["mobilePhone"] = data["phone"]
            
            if asaas_data:
                await asaas_client.update_customer(asaas_id, asaas_data)
        
        # Atualizar localmente
        params = {
            "id": customer_id,
            "name": data.get("name"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "address": json.dumps(data["address"]) if "address" in data else None,
            "active": data.get("active")
        }
        
        result = execute_query(UPDATE_ASAAS_CUSTOMER, params, fetch_one=True)
        
        return serialize_row(row_to_dict(result, CUSTOMER_COLUMNS))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str):
    """Remove um cliente (soft delete)."""
    try:
        existing = execute_query(
            SELECT_ASAAS_CUSTOMER_BY_ID, 
            {"id": customer_id}, 
            fetch_one=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        existing_dict = row_to_dict(existing, CUSTOMER_COLUMNS)
        asaas_id = existing_dict.get("asaas_id")
        
        # Remover no Asaas
        if asaas_id:
            try:
                await asaas_client.delete_customer(asaas_id)
            except Exception as e:
                logger.warning(f"Erro ao remover cliente no Asaas: {e}")
        
        # Soft delete local
        execute_query(DELETE_ASAAS_CUSTOMER, {"id": customer_id})
        
        return {"message": "Cliente removido com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers/{customer_id}/payments")
async def get_customer_payments(
    customer_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """Lista pagamentos de um cliente."""
    try:
        params = {"cliente_id": customer_id, "offset": offset, "limit": limit}
        rows = execute_query(SELECT_PAYMENTS_BY_CUSTOMER, params)
        
        columns = [
            "id", "asaas_id", "cliente_id", "value", "status", "due_date",
            "payment_date", "invoice_url", "billing_type", "description", "created_at"
        ]
        
        return [serialize_row(row_to_dict(row, columns)) for row in rows]
        
    except Exception as e:
        logger.error(f"Erro ao buscar pagamentos do cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers/{customer_id}/subscriptions")
async def get_customer_subscriptions(customer_id: str):
    """Lista assinaturas de um cliente."""
    try:
        params = {"cliente_id": customer_id}
        rows = execute_query(SELECT_SUBSCRIPTIONS_BY_CUSTOMER, params)
        
        columns = [
            "id", "asaas_id", "cliente_id", "product_id", "value", "cycle",
            "status", "next_due_date", "billing_type", "description", "created_at"
        ]
        
        return [serialize_row(row_to_dict(row, columns)) for row in rows]
        
    except Exception as e:
        logger.error(f"Erro ao buscar assinaturas do cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PRODUCTS ENDPOINTS
# ============================================================================

PRODUCT_COLUMNS = ["id", "name", "price", "cycle", "active", "created_at"]


@router.get("/products", response_model=PaginatedResponse)
async def list_products(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    active: Optional[bool] = None
):
    """Lista produtos/planos."""
    try:
        params = {"offset": offset, "limit": limit, "active": active}
        
        rows = execute_query(SELECT_ALL_ASAAS_PRODUCTS, params)
        count_result = execute_query(COUNT_ASAAS_PRODUCTS, params, fetch_one=True)
        
        data = [serialize_row(row_to_dict(row, PRODUCT_COLUMNS)) for row in rows]
        total = count_result[0] if count_result else 0
        
        return {
            "data": data,
            "total_count": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total
        }
    except Exception as e:
        logger.error(f"Erro ao listar produtos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/active")
async def list_active_products():
    """Lista produtos ativos."""
    try:
        rows = execute_query(SELECT_ACTIVE_ASAAS_PRODUCTS, {})
        return [serialize_row(row_to_dict(row, PRODUCT_COLUMNS)) for row in rows]
    except Exception as e:
        logger.error(f"Erro ao listar produtos ativos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/products")
async def create_product(product: AsaasProductCreate):
    """Cria um novo produto/plano."""
    try:
        params = {
            "name": product.name,
            "price": product.price,
            "cycle": product.cycle.value,
            "active": product.active
        }
        
        result = execute_query(INSERT_ASAAS_PRODUCT, params, fetch_one=True)
        
        return serialize_row(row_to_dict(result, PRODUCT_COLUMNS))
        
    except Exception as e:
        logger.error(f"Erro ao criar produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{product_id}")
async def get_product(product_id: str):
    """Obtém detalhes de um produto."""
    try:
        row = execute_query(
            SELECT_ASAAS_PRODUCT_BY_ID, 
            {"id": product_id}, 
            fetch_one=True
        )
        if not row:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        return serialize_row(row_to_dict(row, PRODUCT_COLUMNS))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/products/{product_id}")
async def update_product(product_id: str, data: dict):
    """Atualiza um produto."""
    try:
        params = {
            "id": product_id,
            "name": data.get("name"),
            "price": data.get("price"),
            "cycle": data.get("cycle"),
            "active": data.get("active")
        }
        
        result = execute_query(UPDATE_ASAAS_PRODUCT, params, fetch_one=True)
        if not result:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        return serialize_row(row_to_dict(result, PRODUCT_COLUMNS))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/products/{product_id}")
async def delete_product(product_id: str):
    """Remove um produto (soft delete)."""
    try:
        result = execute_query(DELETE_ASAAS_PRODUCT, {"id": product_id}, fetch_one=True)
        if not result:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        return {"message": "Produto removido com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PAYMENTS ENDPOINTS
# ============================================================================

PAYMENT_COLUMNS = [
    "id", "asaas_id", "cliente_id", "value", "status", "due_date",
    "payment_date", "invoice_url", "billing_type", "description", "created_at"
]


@router.get("/payments", response_model=PaginatedResponse)
async def list_payments(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = None,
    customer_id: Optional[str] = None
):
    """Lista cobranças."""
    try:
        params = {
            "offset": offset, 
            "limit": limit, 
            "status": status,
            "cliente_id": customer_id
        }
        
        rows = execute_query(SELECT_ALL_ASAAS_PAYMENTS, params)
        count_result = execute_query(COUNT_ASAAS_PAYMENTS, params, fetch_one=True)
        
        data = [serialize_row(row_to_dict(row, PAYMENT_COLUMNS)) for row in rows]
        total = count_result[0] if count_result else 0
        
        return {
            "data": data,
            "total_count": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total
        }
    except Exception as e:
        logger.error(f"Erro ao listar pagamentos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payments")
async def create_payment(payment: AsaasPaymentCreate):
    """
    Cria uma cobrança no Asaas e salva localmente.
    """
    try:
        # Buscar asaas_id do cliente
        customer = execute_query(
            SELECT_ASAAS_CUSTOMER_BY_ID,
            {"id": payment.customer_id},
            fetch_one=True
        )
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        customer_dict = row_to_dict(customer, CUSTOMER_COLUMNS)
        asaas_customer_id = customer_dict.get("asaas_id")
        
        if not asaas_customer_id:
            raise HTTPException(
                status_code=400, 
                detail="Cliente não está sincronizado com Asaas"
            )
        
        # Criar cobrança no Asaas
        asaas_data = {
            "customer": asaas_customer_id,
            "billingType": payment.billing_type.value,
            "value": float(payment.value),
            "dueDate": payment.due_date.isoformat(),
        }
        if payment.description:
            asaas_data["description"] = payment.description
        if payment.external_reference:
            asaas_data["externalReference"] = payment.external_reference
        if payment.installment_count:
            asaas_data["installmentCount"] = payment.installment_count
            asaas_data["installmentValue"] = float(
                payment.installment_value or payment.value / payment.installment_count
            )
        
        asaas_response = await asaas_client.create_payment(asaas_data)
        
        # Salvar localmente
        params = {
            "asaas_id": asaas_response.get("id"),
            "cliente_id": payment.customer_id,
            "value": payment.value,
            "status": asaas_response.get("status", "PENDING"),
            "due_date": payment.due_date,
            "payment_date": None,
            "invoice_url": asaas_response.get("invoiceUrl"),
            "billing_type": payment.billing_type.value,
            "description": payment.description
        }
        
        result = execute_query(INSERT_ASAAS_PAYMENT, params, fetch_one=True)
        
        response = serialize_row(row_to_dict(result, PAYMENT_COLUMNS))
        
        # Adicionar dados de pagamento do Asaas
        response["bank_slip_url"] = asaas_response.get("bankSlipUrl")
        response["pix_transaction"] = asaas_response.get("pixTransaction")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar pagamento: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    """Obtém detalhes de uma cobrança."""
    try:
        row = execute_query(
            SELECT_ASAAS_PAYMENT_BY_ID, 
            {"id": payment_id}, 
            fetch_one=True
        )
        if not row:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado")
        
        return serialize_row(row_to_dict(row, PAYMENT_COLUMNS))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar pagamento: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/{payment_id}/link")
async def get_payment_link(payment_id: str):
    """Obtém link de pagamento (boleto, PIX QR Code)."""
    try:
        row = execute_query(
            SELECT_ASAAS_PAYMENT_BY_ID, 
            {"id": payment_id}, 
            fetch_one=True
        )
        if not row:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado")
        
        payment_dict = row_to_dict(row, PAYMENT_COLUMNS)
        asaas_id = payment_dict.get("asaas_id")
        
        if not asaas_id:
            raise HTTPException(
                status_code=400, 
                detail="Pagamento não sincronizado com Asaas"
            )
        
        # Buscar dados de pagamento no Asaas
        billing_info = await asaas_client.get_payment_billing_info(asaas_id)
        
        return billing_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar link de pagamento: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payments/{payment_id}/refund")
async def refund_payment(payment_id: str, value: Optional[float] = None):
    """Estorna um pagamento."""
    try:
        row = execute_query(
            SELECT_ASAAS_PAYMENT_BY_ID, 
            {"id": payment_id}, 
            fetch_one=True
        )
        if not row:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado")
        
        payment_dict = row_to_dict(row, PAYMENT_COLUMNS)
        asaas_id = payment_dict.get("asaas_id")
        
        if not asaas_id:
            raise HTTPException(
                status_code=400, 
                detail="Pagamento não sincronizado com Asaas"
            )
        
        # Estornar no Asaas
        asaas_response = await asaas_client.refund_payment(asaas_id, value)
        
        # Atualizar status local
        params = {
            "asaas_id": asaas_id,
            "status": "REFUNDED",
            "payment_date": None
        }
        execute_query(UPDATE_ASAAS_PAYMENT_STATUS, params)
        
        return {"message": "Estorno solicitado com sucesso", "asaas_response": asaas_response}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao estornar pagamento: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/payments/{payment_id}")
async def delete_payment(payment_id: str):
    """Cancela uma cobrança."""
    try:
        row = execute_query(
            SELECT_ASAAS_PAYMENT_BY_ID, 
            {"id": payment_id}, 
            fetch_one=True
        )
        if not row:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado")
        
        payment_dict = row_to_dict(row, PAYMENT_COLUMNS)
        asaas_id = payment_dict.get("asaas_id")
        
        # Cancelar no Asaas
        if asaas_id:
            try:
                await asaas_client.delete_payment(asaas_id)
            except Exception as e:
                logger.warning(f"Erro ao cancelar pagamento no Asaas: {e}")
        
        # Remover local
        execute_query(DELETE_ASAAS_PAYMENT, {"id": payment_id})
        
        return {"message": "Pagamento cancelado com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao cancelar pagamento: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SUBSCRIPTIONS ENDPOINTS
# ============================================================================

SUBSCRIPTION_COLUMNS = [
    "id", "asaas_id", "cliente_id", "product_id", "value", "cycle",
    "status", "next_due_date", "billing_type", "description", "created_at"
]


@router.get("/subscriptions/metrics")
async def get_subscription_metrics():
    """Obtém métricas de assinaturas (MRR, Churn)."""
    try:
        result = execute_query(SELECT_SUBSCRIPTION_METRICS, {}, fetch_one=True)
        
        if result:
            return {
                "total": result[0] or 0,
                "active": result[1] or 0,
                "inactive": result[2] or 0,
                "expired": result[3] or 0,
                "mrr": float(result[4]) if result[4] else 0.0,
                "churn_rate": (
                    round((result[2] + result[3]) / result[0] * 100, 2) 
                    if result[0] > 0 else 0.0
                )
            }
        
        return {
            "total": 0,
            "active": 0,
            "inactive": 0,
            "expired": 0,
            "mrr": 0.0,
            "churn_rate": 0.0
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar métricas de assinaturas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions", response_model=PaginatedResponse)
async def list_subscriptions(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = None,
    customer_id: Optional[str] = None
):
    """Lista assinaturas."""
    try:
        params = {
            "offset": offset, 
            "limit": limit, 
            "status": status,
            "cliente_id": customer_id
        }
        
        rows = execute_query(SELECT_ALL_ASAAS_SUBSCRIPTIONS, params)
        count_result = execute_query(COUNT_ASAAS_SUBSCRIPTIONS, params, fetch_one=True)
        
        data = [serialize_row(row_to_dict(row, SUBSCRIPTION_COLUMNS)) for row in rows]
        total = count_result[0] if count_result else 0
        
        return {
            "data": data,
            "total_count": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total
        }
    except Exception as e:
        logger.error(f"Erro ao listar assinaturas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions")
async def create_subscription(subscription: AsaasSubscriptionCreate):
    """
    Cria uma assinatura no Asaas e salva localmente.
    """
    try:
        # Buscar asaas_id do cliente
        customer = execute_query(
            SELECT_ASAAS_CUSTOMER_BY_ID,
            {"id": subscription.customer_id},
            fetch_one=True
        )
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        customer_dict = row_to_dict(customer, CUSTOMER_COLUMNS)
        asaas_customer_id = customer_dict.get("asaas_id")
        
        if not asaas_customer_id:
            raise HTTPException(
                status_code=400, 
                detail="Cliente não está sincronizado com Asaas"
            )
        
        # Criar assinatura no Asaas
        asaas_data = {
            "customer": asaas_customer_id,
            "billingType": subscription.billing_type.value,
            "value": float(subscription.value),
            "nextDueDate": subscription.next_due_date.isoformat(),
            "cycle": subscription.cycle.value,
        }
        if subscription.description:
            asaas_data["description"] = subscription.description
        if subscription.external_reference:
            asaas_data["externalReference"] = subscription.external_reference
        
        asaas_response = await asaas_client.create_subscription(asaas_data)
        
        # Salvar localmente
        params = {
            "asaas_id": asaas_response.get("id"),
            "cliente_id": subscription.customer_id,
            "product_id": subscription.product_id,
            "value": subscription.value,
            "cycle": subscription.cycle.value,
            "status": asaas_response.get("status", "ACTIVE"),
            "next_due_date": subscription.next_due_date,
            "billing_type": subscription.billing_type.value,
            "description": subscription.description
        }
        
        result = execute_query(INSERT_ASAAS_SUBSCRIPTION, params, fetch_one=True)
        
        return serialize_row(row_to_dict(result, SUBSCRIPTION_COLUMNS))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar assinatura: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(subscription_id: str):
    """Obtém detalhes de uma assinatura."""
    try:
        row = execute_query(
            SELECT_ASAAS_SUBSCRIPTION_BY_ID, 
            {"id": subscription_id}, 
            fetch_one=True
        )
        if not row:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        return serialize_row(row_to_dict(row, SUBSCRIPTION_COLUMNS))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar assinatura: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/subscriptions/{subscription_id}")
async def update_subscription(subscription_id: str, data: AsaasSubscriptionUpdate):
    """Atualiza uma assinatura."""
    try:
        existing = execute_query(
            SELECT_ASAAS_SUBSCRIPTION_BY_ID, 
            {"id": subscription_id}, 
            fetch_one=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        existing_dict = row_to_dict(existing, SUBSCRIPTION_COLUMNS)
        asaas_id = existing_dict.get("asaas_id")
        
        # Atualizar no Asaas
        if asaas_id:
            asaas_data = {}
            if data.value is not None:
                asaas_data["value"] = float(data.value)
            if data.next_due_date is not None:
                asaas_data["nextDueDate"] = data.next_due_date.isoformat()
            if data.cycle is not None:
                asaas_data["cycle"] = data.cycle.value
            if data.billing_type is not None:
                asaas_data["billingType"] = data.billing_type.value
            
            if asaas_data:
                await asaas_client.update_subscription(asaas_id, asaas_data)
        
        # Atualizar localmente
        params = {
            "id": subscription_id,
            "value": data.value,
            "next_due_date": data.next_due_date,
            "cycle": data.cycle.value if data.cycle else None,
            "billing_type": data.billing_type.value if data.billing_type else None,
            "description": data.description,
            "status": None
        }
        
        result = execute_query(UPDATE_ASAAS_SUBSCRIPTION, params, fetch_one=True)
        
        return serialize_row(row_to_dict(result, SUBSCRIPTION_COLUMNS))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar assinatura: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/{subscription_id}/pause")
async def pause_subscription(subscription_id: str):
    """Pausa uma assinatura."""
    try:
        existing = execute_query(
            SELECT_ASAAS_SUBSCRIPTION_BY_ID, 
            {"id": subscription_id}, 
            fetch_one=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        existing_dict = row_to_dict(existing, SUBSCRIPTION_COLUMNS)
        asaas_id = existing_dict.get("asaas_id")
        
        # Pausar no Asaas (desativar)
        if asaas_id:
            await asaas_client.update_subscription(asaas_id, {"status": "INACTIVE"})
        
        # Atualizar localmente
        params = {
            "id": subscription_id,
            "status": "INACTIVE",
            "value": None,
            "next_due_date": None,
            "cycle": None,
            "billing_type": None,
            "description": None
        }
        
        result = execute_query(UPDATE_ASAAS_SUBSCRIPTION, params, fetch_one=True)
        
        return {"message": "Assinatura pausada", "subscription": serialize_row(row_to_dict(result, SUBSCRIPTION_COLUMNS))}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao pausar assinatura: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/{subscription_id}/resume")
async def resume_subscription(subscription_id: str):
    """Reativa uma assinatura pausada."""
    try:
        existing = execute_query(
            SELECT_ASAAS_SUBSCRIPTION_BY_ID, 
            {"id": subscription_id}, 
            fetch_one=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        existing_dict = row_to_dict(existing, SUBSCRIPTION_COLUMNS)
        asaas_id = existing_dict.get("asaas_id")
        
        # Reativar no Asaas
        if asaas_id:
            await asaas_client.update_subscription(asaas_id, {"status": "ACTIVE"})
        
        # Atualizar localmente
        params = {
            "id": subscription_id,
            "status": "ACTIVE",
            "value": None,
            "next_due_date": None,
            "cycle": None,
            "billing_type": None,
            "description": None
        }
        
        result = execute_query(UPDATE_ASAAS_SUBSCRIPTION, params, fetch_one=True)
        
        return {"message": "Assinatura reativada", "subscription": serialize_row(row_to_dict(result, SUBSCRIPTION_COLUMNS))}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao reativar assinatura: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(subscription_id: str):
    """Cancela uma assinatura."""
    try:
        existing = execute_query(
            SELECT_ASAAS_SUBSCRIPTION_BY_ID, 
            {"id": subscription_id}, 
            fetch_one=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        existing_dict = row_to_dict(existing, SUBSCRIPTION_COLUMNS)
        asaas_id = existing_dict.get("asaas_id")
        
        # Cancelar no Asaas
        if asaas_id:
            try:
                await asaas_client.delete_subscription(asaas_id)
            except Exception as e:
                logger.warning(f"Erro ao cancelar assinatura no Asaas: {e}")
        
        # Soft delete local
        execute_query(DELETE_ASAAS_SUBSCRIPTION, {"id": subscription_id})
        
        return {"message": "Assinatura cancelada com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao cancelar assinatura: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions/{subscription_id}/payments")
async def get_subscription_payments(
    subscription_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """Lista cobranças de uma assinatura."""
    try:
        existing = execute_query(
            SELECT_ASAAS_SUBSCRIPTION_BY_ID, 
            {"id": subscription_id}, 
            fetch_one=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        existing_dict = row_to_dict(existing, SUBSCRIPTION_COLUMNS)
        asaas_id = existing_dict.get("asaas_id")
        
        if not asaas_id:
            raise HTTPException(
                status_code=400, 
                detail="Assinatura não sincronizada com Asaas"
            )
        
        # Buscar cobranças no Asaas
        payments = await asaas_client.get_subscription_payments(asaas_id, offset, limit)
        
        return payments
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar pagamentos da assinatura: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@router.get("/dashboard")
async def get_dashboard():
    """Obtém métricas gerais do dashboard."""
    try:
        # MRR
        mrr_result = execute_query(SELECT_MRR, {}, fetch_one=True)
        mrr = float(mrr_result[0]) if mrr_result and mrr_result[0] else 0.0
        
        # Clientes
        customers_result = execute_query(
            COUNT_ASAAS_CUSTOMERS, 
            {"active": True}, 
            fetch_one=True
        )
        total_customers = customers_result[0] if customers_result else 0
        
        # Assinaturas ativas
        subscriptions_result = execute_query(
            COUNT_ASAAS_SUBSCRIPTIONS, 
            {"status": "ACTIVE", "cliente_id": None}, 
            fetch_one=True
        )
        active_subscriptions = subscriptions_result[0] if subscriptions_result else 0
        
        # Pagamentos pendentes e vencidos
        pending_result = execute_query(
            COUNT_ASAAS_PAYMENTS, 
            {"status": "PENDING", "cliente_id": None}, 
            fetch_one=True
        )
        overdue_result = execute_query(
            COUNT_ASAAS_PAYMENTS, 
            {"status": "OVERDUE", "cliente_id": None}, 
            fetch_one=True
        )
        
        pending_payments = pending_result[0] if pending_result else 0
        overdue_payments = overdue_result[0] if overdue_result else 0
        
        # Estatísticas de pagamentos
        stats_result = execute_query(
            SELECT_PAYMENT_STATS, 
            {"start_date": None, "end_date": None}, 
            fetch_one=True
        )
        
        payment_stats = {
            "total": stats_result[0] if stats_result else 0,
            "pending": stats_result[1] if stats_result else 0,
            "received": stats_result[2] if stats_result else 0,
            "overdue": stats_result[3] if stats_result else 0,
            "refunded": stats_result[4] if stats_result else 0,
            "total_value": float(stats_result[5]) if stats_result and stats_result[5] else 0.0,
            "received_value": float(stats_result[6]) if stats_result and stats_result[6] else 0.0,
            "pending_value": float(stats_result[7]) if stats_result and stats_result[7] else 0.0
        }
        
        return {
            "mrr": mrr,
            "total_customers": total_customers,
            "active_subscriptions": active_subscriptions,
            "pending_payments": pending_payments,
            "overdue_payments": overdue_payments,
            "payment_stats": payment_stats
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/mrr")
async def get_mrr():
    """Obtém MRR (Monthly Recurring Revenue)."""
    try:
        result = execute_query(SELECT_MRR, {}, fetch_one=True)
        mrr = float(result[0]) if result and result[0] else 0.0
        
        return {"mrr": mrr}
        
    except Exception as e:
        logger.error(f"Erro ao buscar MRR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/payments")
async def get_payments_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Obtém resumo de pagamentos."""
    try:
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        result = execute_query(SELECT_PAYMENT_STATS, params, fetch_one=True)
        
        if result:
            return {
                "total": result[0] or 0,
                "pending": result[1] or 0,
                "received": result[2] or 0,
                "overdue": result[3] or 0,
                "refunded": result[4] or 0,
                "total_value": float(result[5]) if result[5] else 0.0,
                "received_value": float(result[6]) if result[6] else 0.0,
                "pending_value": float(result[7]) if result[7] else 0.0
            }
        
        return {
            "total": 0,
            "pending": 0,
            "received": 0,
            "overdue": 0,
            "refunded": 0,
            "total_value": 0.0,
            "received_value": 0.0,
            "pending_value": 0.0
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar resumo de pagamentos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/overdue")
async def get_overdue_customers(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """Lista clientes inadimplentes."""
    try:
        params = {"offset": offset, "limit": limit}
        rows = execute_query(SELECT_OVERDUE_CUSTOMERS, params)
        
        columns = ["id", "asaas_id", "name", "email", "cpf_cnpj", "overdue_count", "overdue_value"]
        
        return [serialize_row(row_to_dict(row, columns)) for row in rows]
        
    except Exception as e:
        logger.error(f"Erro ao buscar inadimplentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBHOOKS ENDPOINTS
# ============================================================================

@router.post("/webhooks/asaas")
async def receive_asaas_webhook(event: AsaasWebhookEvent):
    """
    Recebe eventos de webhook do Asaas.
    Eventos suportados:
    - PAYMENT_RECEIVED
    - PAYMENT_CONFIRMED
    - PAYMENT_OVERDUE
    - PAYMENT_REFUNDED
    - PAYMENT_DELETED
    """
    try:
        logger.info(f"Webhook recebido: {event.event}")
        
        if event.payment:
            asaas_id = event.payment.get("id")
            status = event.payment.get("status")
            payment_date = event.payment.get("paymentDate")
            
            if asaas_id and status:
                params = {
                    "asaas_id": asaas_id,
                    "status": status,
                    "payment_date": payment_date
                }
                
                execute_query(UPDATE_ASAAS_PAYMENT_STATUS, params)
                logger.info(f"Pagamento {asaas_id} atualizado para {status}")
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SYNC ENDPOINTS
# ============================================================================

@router.post("/sync/customers")
async def sync_customers_from_asaas(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Sincroniza clientes do Asaas para o banco local.
    Útil para importar clientes já existentes no Asaas.
    """
    try:
        # Buscar clientes do Asaas
        asaas_response = await asaas_client.list_customers(offset=offset, limit=limit)
        
        synced = 0
        errors = []
        
        for customer in asaas_response.get("data", []):
            try:
                params = {
                    "asaas_id": customer.get("id"),
                    "name": customer.get("name"),
                    "email": customer.get("email"),
                    "cpf_cnpj": customer.get("cpfCnpj"),
                    "phone": customer.get("mobilePhone") or customer.get("phone"),
                    "address": json.dumps({
                        "street": customer.get("address"),
                        "number": customer.get("addressNumber"),
                        "complement": customer.get("complement"),
                        "province": customer.get("province"),
                        "postal_code": customer.get("postalCode")
                    }),
                    "active": not customer.get("deleted", False)
                }
                
                execute_query(INSERT_ASAAS_CUSTOMER, params)
                synced += 1
                
            except Exception as e:
                errors.append({
                    "asaas_id": customer.get("id"),
                    "error": str(e)
                })
        
        return {
            "synced": synced,
            "errors": errors,
            "has_more": asaas_response.get("hasMore", False)
        }
        
    except Exception as e:
        logger.error(f"Erro ao sincronizar clientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/payments")
async def sync_payments_from_asaas(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = None
):
    """
    Sincroniza pagamentos do Asaas para o banco local.
    Útil para importar pagamentos já existentes no Asaas.
    """
    try:
        # Buscar pagamentos do Asaas
        asaas_response = await asaas_client.list_payments(
            offset=offset, 
            limit=limit,
            status=status
        )
        
        synced = 0
        errors = []
        skipped = 0
        
        for payment in asaas_response.get("data", []):
            try:
                asaas_customer_id = payment.get("customer")
                
                # Buscar cliente local pelo asaas_id
                customer = execute_query(
                    SELECT_ASAAS_CUSTOMER_BY_ASAAS_ID,
                    {"asaas_id": asaas_customer_id},
                    fetch_one=True
                )
                
                if not customer:
                    skipped += 1
                    continue
                
                customer_dict = row_to_dict(customer, CUSTOMER_COLUMNS)
                
                params = {
                    "asaas_id": payment.get("id"),
                    "cliente_id": customer_dict.get("id"),
                    "value": payment.get("value"),
                    "status": payment.get("status"),
                    "due_date": payment.get("dueDate"),
                    "payment_date": payment.get("paymentDate"),
                    "invoice_url": payment.get("invoiceUrl"),
                    "billing_type": payment.get("billingType"),
                    "description": payment.get("description")
                }
                
                execute_query(INSERT_OR_UPDATE_ASAAS_PAYMENT, params)
                synced += 1
                
            except Exception as e:
                errors.append({
                    "asaas_id": payment.get("id"),
                    "error": str(e)
                })
        
        return {
            "synced": synced,
            "skipped": skipped,
            "errors": errors,
            "has_more": asaas_response.get("hasMore", False)
        }
        
    except Exception as e:
        logger.error(f"Erro ao sincronizar pagamentos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/subscriptions")
async def sync_subscriptions_from_asaas(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = None
):
    """
    Sincroniza assinaturas do Asaas para o banco local.
    Útil para importar assinaturas já existentes no Asaas.
    """
    try:
        # Buscar assinaturas do Asaas
        asaas_response = await asaas_client.list_subscriptions(
            offset=offset, 
            limit=limit,
            status=status
        )
        
        synced = 0
        errors = []
        skipped = 0
        
        for subscription in asaas_response.get("data", []):
            try:
                asaas_customer_id = subscription.get("customer")
                
                # Buscar cliente local pelo asaas_id
                customer = execute_query(
                    SELECT_ASAAS_CUSTOMER_BY_ASAAS_ID,
                    {"asaas_id": asaas_customer_id},
                    fetch_one=True
                )
                
                if not customer:
                    skipped += 1
                    continue
                
                customer_dict = row_to_dict(customer, CUSTOMER_COLUMNS)
                
                params = {
                    "asaas_id": subscription.get("id"),
                    "cliente_id": customer_dict.get("id"),
                    "product_id": None,  # Produto não sincronizado automaticamente
                    "value": subscription.get("value"),
                    "cycle": subscription.get("cycle"),
                    "status": subscription.get("status"),
                    "next_due_date": subscription.get("nextDueDate"),
                    "billing_type": subscription.get("billingType"),
                    "description": subscription.get("description")
                }
                
                execute_query(INSERT_OR_UPDATE_ASAAS_SUBSCRIPTION, params)
                synced += 1
                
            except Exception as e:
                errors.append({
                    "asaas_id": subscription.get("id"),
                    "error": str(e)
                })
        
        return {
            "synced": synced,
            "skipped": skipped,
            "errors": errors,
            "has_more": asaas_response.get("hasMore", False)
        }
        
    except Exception as e:
        logger.error(f"Erro ao sincronizar assinaturas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/all")
async def sync_all_from_asaas(
    limit: int = Query(100, ge=1, le=500)
):
    """
    Sincroniza todos os dados do Asaas (clientes, pagamentos, assinaturas).
    Executa em sequência para garantir dependências.
    """
    try:
        results = {
            "customers": {"synced": 0, "errors": 0, "has_more": True},
            "payments": {"synced": 0, "errors": 0, "skipped": 0, "has_more": True},
            "subscriptions": {"synced": 0, "errors": 0, "skipped": 0, "has_more": True}
        }
        
        # 1. Sincronizar clientes
        offset = 0
        while results["customers"]["has_more"]:
            response = await asaas_client.list_customers(offset=offset, limit=limit)
            
            for customer in response.get("data", []):
                try:
                    params = {
                        "asaas_id": customer.get("id"),
                        "name": customer.get("name"),
                        "email": customer.get("email"),
                        "cpf_cnpj": customer.get("cpfCnpj"),
                        "phone": customer.get("mobilePhone") or customer.get("phone"),
                        "address": json.dumps({
                            "street": customer.get("address"),
                            "number": customer.get("addressNumber"),
                            "complement": customer.get("complement"),
                            "province": customer.get("province"),
                            "postal_code": customer.get("postalCode")
                        }),
                        "active": not customer.get("deleted", False)
                    }
                    execute_query(INSERT_ASAAS_CUSTOMER, params)
                    results["customers"]["synced"] += 1
                except Exception:
                    results["customers"]["errors"] += 1
            
            results["customers"]["has_more"] = response.get("hasMore", False)
            offset += limit
            
            # Limite de segurança
            if offset > 10000:
                break
        
        # 2. Sincronizar pagamentos
        offset = 0
        while results["payments"]["has_more"]:
            response = await asaas_client.list_payments(offset=offset, limit=limit)
            
            for payment in response.get("data", []):
                try:
                    customer = execute_query(
                        SELECT_ASAAS_CUSTOMER_BY_ASAAS_ID,
                        {"asaas_id": payment.get("customer")},
                        fetch_one=True
                    )
                    
                    if not customer:
                        results["payments"]["skipped"] += 1
                        continue
                    
                    customer_dict = row_to_dict(customer, CUSTOMER_COLUMNS)
                    
                    params = {
                        "asaas_id": payment.get("id"),
                        "cliente_id": customer_dict.get("id"),
                        "value": payment.get("value"),
                        "status": payment.get("status"),
                        "due_date": payment.get("dueDate"),
                        "payment_date": payment.get("paymentDate"),
                        "invoice_url": payment.get("invoiceUrl"),
                        "billing_type": payment.get("billingType"),
                        "description": payment.get("description")
                    }
                    execute_query(INSERT_OR_UPDATE_ASAAS_PAYMENT, params)
                    results["payments"]["synced"] += 1
                except Exception:
                    results["payments"]["errors"] += 1
            
            results["payments"]["has_more"] = response.get("hasMore", False)
            offset += limit
            
            if offset > 10000:
                break
        
        # 3. Sincronizar assinaturas
        offset = 0
        while results["subscriptions"]["has_more"]:
            response = await asaas_client.list_subscriptions(offset=offset, limit=limit)
            
            for subscription in response.get("data", []):
                try:
                    customer = execute_query(
                        SELECT_ASAAS_CUSTOMER_BY_ASAAS_ID,
                        {"asaas_id": subscription.get("customer")},
                        fetch_one=True
                    )
                    
                    if not customer:
                        results["subscriptions"]["skipped"] += 1
                        continue
                    
                    customer_dict = row_to_dict(customer, CUSTOMER_COLUMNS)
                    
                    params = {
                        "asaas_id": subscription.get("id"),
                        "cliente_id": customer_dict.get("id"),
                        "product_id": None,
                        "value": subscription.get("value"),
                        "cycle": subscription.get("cycle"),
                        "status": subscription.get("status"),
                        "next_due_date": subscription.get("nextDueDate"),
                        "billing_type": subscription.get("billingType"),
                        "description": subscription.get("description")
                    }
                    execute_query(INSERT_OR_UPDATE_ASAAS_SUBSCRIPTION, params)
                    results["subscriptions"]["synced"] += 1
                except Exception:
                    results["subscriptions"]["errors"] += 1
            
            results["subscriptions"]["has_more"] = response.get("hasMore", False)
            offset += limit
            
            if offset > 10000:
                break
        
        return results
        
    except Exception as e:
        logger.error(f"Erro ao sincronizar todos os dados: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CHURN ENDPOINT
# ============================================================================

@router.get("/dashboard/churn")
async def get_churn_rate(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Obtém taxa de churn de assinaturas."""
    try:
        # Churn geral
        overall_result = execute_query(SELECT_OVERALL_CHURN, {}, fetch_one=True)
        
        overall = {
            "active": overall_result[0] if overall_result else 0,
            "churned": overall_result[1] if overall_result else 0,
            "total": overall_result[2] if overall_result else 0,
            "churn_rate": float(overall_result[3]) if overall_result and overall_result[3] else 0.0
        }
        
        # Churn por mês (se datas fornecidas)
        monthly = []
        if start_date and end_date:
            params = {"start_date": start_date, "end_date": end_date}
            rows = execute_query(SELECT_CHURN_RATE, params)
            
            for row in rows:
                monthly.append({
                    "month": row[0].isoformat() if row[0] else None,
                    "new_subscriptions": row[1] or 0,
                    "churned": row[2] or 0,
                    "churn_rate": float(row[3]) if row[3] else 0.0
                })
        
        return {
            "overall": overall,
            "monthly": monthly
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar churn rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# REVENUE ENDPOINT
# ============================================================================

@router.get("/dashboard/revenue")
async def get_revenue_by_period(
    start_date: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Data final (YYYY-MM-DD)")
):
    """Obtém receita por período (mensal)."""
    try:
        params = {"start_date": start_date, "end_date": end_date}
        rows = execute_query(SELECT_REVENUE_BY_PERIOD, params)
        
        data = []
        total_revenue = 0.0
        total_payments = 0
        
        for row in rows:
            month_value = float(row[2]) if row[2] else 0.0
            data.append({
                "month": row[0].isoformat() if row[0] else None,
                "payment_count": row[1] or 0,
                "total_value": month_value
            })
            total_revenue += month_value
            total_payments += row[1] or 0
        
        return {
            "data": data,
            "total_revenue": total_revenue,
            "total_payments": total_payments,
            "period": {
                "start": start_date,
                "end": end_date
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar receita por período: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ACCOUNT INFO ENDPOINT
# ============================================================================

@router.get("/account")
async def get_asaas_account_info():
    """Obtém informações da conta Asaas."""
    try:
        account_info = await asaas_client.get_account_info()
        balance = await asaas_client.get_balance()
        
        return {
            "account": account_info,
            "balance": balance
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar informações da conta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

