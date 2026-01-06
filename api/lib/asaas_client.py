"""
Cliente HTTP para integração com Asaas API.

Fornece métodos para interagir com a API do Asaas para:
- Clientes (Customers)
- Cobranças (Payments)
- Assinaturas (Subscriptions)
- Links de Pagamento (Payment Links)
"""

import os
import httpx
import logging
from typing import Optional, Dict, Any, List
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

ASAAS_API_KEY = os.getenv("ASAAS_API_KEY", "")
ASAAS_SANDBOX = os.getenv("ASAAS_SANDBOX", "true").lower() == "true"

ASAAS_BASE_URL = (
    "https://api-sandbox.asaas.com/v3"
    if ASAAS_SANDBOX
    else "https://api.asaas.com/v3"
)

logger.info(f"🔧 Asaas Config: Sandbox={ASAAS_SANDBOX}, API_KEY={'***' + ASAAS_API_KEY[-4:] if ASAAS_API_KEY else 'NOT_SET'}")

# Timeout para requisições (segundos)
TIMEOUT = 30.0

# Configuração de retry
MAX_RETRIES = 3
RETRY_DELAY = 2  # segundos


# ============================================================================
# HELPERS
# ============================================================================

def get_asaas_headers() -> Dict[str, str]:
    """Retorna headers para autenticação na API Asaas."""
    headers = {
        "access_token": ASAAS_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "ecosys-payments/1.0"
    }
    logger.debug(f"🔑 Headers gerados: access_token={'***' + ASAAS_API_KEY[-4:] if ASAAS_API_KEY else 'NOT_SET'}")
    return headers


def with_retry(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
    """Decorator para retry com backoff exponencial."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    last_exception = e
                    wait_time = delay * (2 ** attempt)
                    logger.warning(
                        f"Tentativa {attempt + 1}/{max_retries} falhou: {e}. "
                        f"Aguardando {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                except httpx.HTTPStatusError as e:
                    # Não fazer retry em erros de cliente (4xx)
                    if 400 <= e.response.status_code < 500:
                        raise
                    last_exception = e
                    wait_time = delay * (2 ** attempt)
                    logger.warning(
                        f"Tentativa {attempt + 1}/{max_retries} falhou: {e}. "
                        f"Aguardando {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
            raise last_exception
        return wrapper
    return decorator


# ============================================================================
# CLIENTE ASAAS
# ============================================================================

class AsaasClient:
    """Cliente HTTP para API do Asaas."""

    def __init__(self):
        # Recarregar variáveis de ambiente para garantir
        from dotenv import load_dotenv
        load_dotenv()

        global ASAAS_API_KEY, ASAAS_SANDBOX, ASAAS_BASE_URL
        ASAAS_API_KEY = os.getenv("ASAAS_API_KEY", "")
        ASAAS_SANDBOX = os.getenv("ASAAS_SANDBOX", "true").lower() == "true"
        ASAAS_BASE_URL = (
            "https://api-sandbox.asaas.com/v3"
            if ASAAS_SANDBOX
            else "https://api.asaas.com/v3"
        )

        self.base_url = ASAAS_BASE_URL
        self.headers = get_asaas_headers()

        # Validação da configuração
        if not ASAAS_API_KEY or ASAAS_API_KEY == "":
            logger.error("❌ ASAAS_API_KEY não configurada. Verifique as variáveis de ambiente.")
            raise ValueError("ASAAS_API_KEY não configurada. Verifique as variáveis de ambiente.")

        logger.info(f"✅ AsaasClient inicializado - Ambiente: {'Sandbox' if ASAAS_SANDBOX else 'Produção'} - Headers: {len(self.headers)} campos")

    @with_retry()
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Faz requisição para a API do Asaas.

        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint da API (ex: /customers)
            data: Dados para enviar no body (POST/PUT)
            params: Query parameters (GET)

        Returns:
            Resposta da API como dict
        """
        url = f"{self.base_url}{endpoint}"

        # Log dos headers (sem expor a API key completa)
        safe_headers = {k: (v if k != "access_token" else "***" + v[-4:]) for k, v in self.headers.items()}
        logger.info(f"📡 {method} {url} - Headers: {safe_headers}")

        if data:
            logger.info(f"📤 Data: {data}")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Usar headers da instância
            logger.debug(f"📤 Enviando headers: { {k: (v if k != 'access_token' else '***' + v[-4:]) for k, v in self.headers.items()} }")

            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params
            )

            logger.info(f"📥 Response Status: {response.status_code}")

            response.raise_for_status()
            return response.json()

    # ========================================================================
    # CUSTOMERS (CLIENTES)
    # ========================================================================

    async def list_customers(
        self,
        offset: int = 0,
        limit: int = 100,
        name: Optional[str] = None,
        email: Optional[str] = None,
        cpf_cnpj: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lista clientes do Asaas."""
        params = {"offset": offset, "limit": limit}
        if name:
            params["name"] = name
        if email:
            params["email"] = email
        if cpf_cnpj:
            params["cpfCnpj"] = cpf_cnpj

        return await self._request("GET", "/customers", params=params)

    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Obtém detalhes de um cliente."""
        return await self._request("GET", f"/customers/{customer_id}")

    async def create_customer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria um novo cliente no Asaas.

        Args:
            data: {
                "name": str (obrigatório),
                "cpfCnpj": str (obrigatório),
                "email": str,
                "phone": str,
                "mobilePhone": str,
                "address": str,
                "addressNumber": str,
                "complement": str,
                "province": str,
                "postalCode": str,
                "externalReference": str,
                "notificationDisabled": bool,
                "additionalEmails": str
            }
        """
        logger.info(f"Enviando dados para criação de cliente: {data}")
        try:
            result = await self._request("POST", "/customers", data=data)
            logger.info(f"Cliente criado com sucesso: {result.get('id')}")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP {e.response.status_code} ao criar cliente: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao criar cliente: {e}")
            raise

    async def update_customer(
        self, customer_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Atualiza um cliente existente."""
        return await self._request("PUT", f"/customers/{customer_id}", data=data)

    async def test_connection(self) -> bool:
        """Testa a conexão com a API do Asaas."""
        try:
            # Tenta fazer uma requisição simples para testar
            await self.list_customers(limit=1)
            logger.info("✅ Conexão com Asaas estabelecida")
            return True
        except Exception as e:
            logger.error(f"❌ Falha na conexão com Asaas: {e}")
            return False

    # ========================================================================
    # PAYMENTS (COBRANÇAS)
    # ========================================================================

    async def list_payments(
        self,
        offset: int = 0,
        limit: int = 100,
        customer: Optional[str] = None,
        status: Optional[str] = None,
        billing_type: Optional[str] = None,
        date_created_ge: Optional[str] = None,
        date_created_le: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lista cobranças."""
        params = {"offset": offset, "limit": limit}
        if customer:
            params["customer"] = customer
        if status:
            params["status"] = status
        if billing_type:
            params["billingType"] = billing_type
        if date_created_ge:
            params["dateCreated[ge]"] = date_created_ge
        if date_created_le:
            params["dateCreated[le]"] = date_created_le

        return await self._request("GET", "/payments", params=params)

    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Obtém detalhes de uma cobrança."""
        return await self._request("GET", f"/payments/{payment_id}")

    async def create_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria uma nova cobrança.

        Args:
            data: {
                "customer": str (obrigatório - ID do cliente Asaas),
                "billingType": str (BOLETO, CREDIT_CARD, PIX, UNDEFINED),
                "value": float (obrigatório),
                "dueDate": str (obrigatório - YYYY-MM-DD),
                "description": str,
                "externalReference": str,
                "installmentCount": int,
                "installmentValue": float,
                "discount": dict,
                "interest": dict,
                "fine": dict
            }
        """
        return await self._request("POST", "/payments", data=data)

    async def update_payment(
        self, payment_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Atualiza uma cobrança pendente."""
        return await self._request("PUT", f"/payments/{payment_id}", data=data)

    async def delete_payment(self, payment_id: str) -> Dict[str, Any]:
        """Cancela uma cobrança."""
        return await self._request("DELETE", f"/payments/{payment_id}")

    async def get_payment_billing_info(self, payment_id: str) -> Dict[str, Any]:
        """Obtém linha digitável do boleto ou QR Code do PIX."""
        return await self._request("GET", f"/payments/{payment_id}/billingInfo")

    async def get_payment_pix_qrcode(self, payment_id: str) -> Dict[str, Any]:
        """Obtém QR Code do PIX."""
        return await self._request("GET", f"/payments/{payment_id}/pixQrCode")

    async def refund_payment(
        self, payment_id: str, value: Optional[float] = None
    ) -> Dict[str, Any]:
        """Estorna um pagamento."""
        data = {}
        if value:
            data["value"] = value
        return await self._request("POST", f"/payments/{payment_id}/refund", data=data)

    # ========================================================================
    # SUBSCRIPTIONS (ASSINATURAS)
    # ========================================================================

    async def list_subscriptions(
        self,
        offset: int = 0,
        limit: int = 100,
        customer: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lista assinaturas."""
        params = {"offset": offset, "limit": limit}
        if customer:
            params["customer"] = customer
        if status:
            params["status"] = status

        return await self._request("GET", "/subscriptions", params=params)

    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Obtém detalhes de uma assinatura."""
        return await self._request("GET", f"/subscriptions/{subscription_id}")

    async def create_subscription(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria uma nova assinatura.

        Args:
            data: {
                "customer": str (obrigatório - ID do cliente Asaas),
                "billingType": str (BOLETO, CREDIT_CARD, PIX, UNDEFINED),
                "value": float (obrigatório),
                "nextDueDate": str (obrigatório - YYYY-MM-DD),
                "cycle": str (WEEKLY, BIWEEKLY, MONTHLY, QUARTERLY, SEMIANNUALLY, YEARLY),
                "description": str,
                "externalReference": str,
                "discount": dict,
                "interest": dict,
                "fine": dict
            }
        """
        return await self._request("POST", "/subscriptions", data=data)

    async def update_subscription(
        self, subscription_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Atualiza uma assinatura."""
        return await self._request(
            "PUT", f"/subscriptions/{subscription_id}", data=data
        )

    async def delete_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancela uma assinatura."""
        return await self._request("DELETE", f"/subscriptions/{subscription_id}")

    async def get_subscription_payments(
        self,
        subscription_id: str,
        offset: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Lista cobranças de uma assinatura."""
        params = {"offset": offset, "limit": limit}
        return await self._request(
            "GET", f"/subscriptions/{subscription_id}/payments", params=params
        )

    # ========================================================================
    # PAYMENT LINKS (LINKS DE PAGAMENTO)
    # ========================================================================

    async def list_payment_links(
        self,
        offset: int = 0,
        limit: int = 100,
        active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Lista links de pagamento."""
        params = {"offset": offset, "limit": limit}
        if active is not None:
            params["active"] = active

        return await self._request("GET", "/paymentLinks", params=params)

    async def get_payment_link(self, link_id: str) -> Dict[str, Any]:
        """Obtém detalhes de um link de pagamento."""
        return await self._request("GET", f"/paymentLinks/{link_id}")

    async def create_payment_link(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria um link de pagamento.

        Args:
            data: {
                "name": str (obrigatório),
                "billingType": str (BOLETO, CREDIT_CARD, PIX, UNDEFINED),
                "chargeType": str (DETACHED, RECURRENT, INSTALLMENT),
                "value": float,
                "dueDateLimitDays": int,
                "subscriptionCycle": str,
                "maxInstallmentCount": int,
                "description": str
            }
        """
        return await self._request("POST", "/paymentLinks", data=data)

    async def update_payment_link(
        self, link_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Atualiza um link de pagamento."""
        return await self._request("PUT", f"/paymentLinks/{link_id}", data=data)

    async def delete_payment_link(self, link_id: str) -> Dict[str, Any]:
        """Remove um link de pagamento."""
        return await self._request("DELETE", f"/paymentLinks/{link_id}")

    # ========================================================================
    # ACCOUNT INFO
    # ========================================================================

    async def get_account_info(self) -> Dict[str, Any]:
        """Obtém informações da conta Asaas."""
        return await self._request("GET", "/myAccount")

    async def get_balance(self) -> Dict[str, Any]:
        """Obtém saldo da conta."""
        return await self._request("GET", "/finance/balance")


# ============================================================================
# INSTÂNCIA GLOBAL
# ============================================================================

asaas_client = AsaasClient()


# ============================================================================
# FUNÇÕES DE CONVENIÊNCIA
# ============================================================================

async def sync_customer_to_asaas(
    name: str,
    cpf_cnpj: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    external_reference: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sincroniza um cliente local com o Asaas.
    Se o cliente já existe (por CPF/CNPJ), retorna os dados existentes.
    """
    # Importar função de validação
    from .models import validate_cpf_cnpj

    # Validar CPF/CNPJ
    try:
        cleaned_cpf_cnpj = validate_cpf_cnpj(cpf_cnpj)
    except ValueError as e:
        raise ValueError(f"CPF/CNPJ inválido: {e}")

    # Primeiro, tenta encontrar o cliente
    existing = await asaas_client.list_customers(cpf_cnpj=cleaned_cpf_cnpj)
    
    if existing and len(existing.get("data", [])) > 0:
        logger.info(f"Cliente {cleaned_cpf_cnpj} já existe no Asaas")
        return existing["data"][0]

    # Cliente não existe, criar novo
    customer_data = {
        "name": name,
        "cpfCnpj": cleaned_cpf_cnpj
    }
    
    if email:
        customer_data["email"] = email
    if phone:
        # Limpar telefone para apenas dígitos
        cleaned_phone = ''.join(filter(str.isdigit, phone))
        if len(cleaned_phone) >= 10:  # Pelo menos DDD + número
            customer_data["mobilePhone"] = cleaned_phone
    if external_reference:
        customer_data["externalReference"] = external_reference

    logger.info(f"Criando cliente {cleaned_cpf_cnpj} no Asaas com dados: {customer_data}")
    return await asaas_client.create_customer(customer_data)


async def create_simple_payment(
    customer_id: str,
    value: float,
    due_date: str,
    billing_type: str = "UNDEFINED",
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cria uma cobrança simples.

    Args:
        customer_id: ID do cliente no Asaas
        value: Valor da cobrança
        due_date: Data de vencimento (YYYY-MM-DD)
        billing_type: BOLETO, CREDIT_CARD, PIX ou UNDEFINED
        description: Descrição da cobrança
    """
    data = {
        "customer": customer_id,
        "billingType": billing_type,
        "value": value,
        "dueDate": due_date,
    }
    if description:
        data["description"] = description

    return await asaas_client.create_payment(data)


async def create_simple_subscription(
    customer_id: str,
    value: float,
    next_due_date: str,
    cycle: str = "MONTHLY",
    billing_type: str = "UNDEFINED",
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cria uma assinatura simples.

    Args:
        customer_id: ID do cliente no Asaas
        value: Valor mensal da assinatura
        next_due_date: Próxima data de vencimento (YYYY-MM-DD)
        cycle: MONTHLY, QUARTERLY, SEMIANNUALLY, YEARLY
        billing_type: BOLETO, CREDIT_CARD, PIX ou UNDEFINED
        description: Descrição da assinatura
    """
    data = {
        "customer": customer_id,
        "billingType": billing_type,
        "value": value,
        "nextDueDate": next_due_date,
        "cycle": cycle,
    }
    if description:
        data["description"] = description

    return await asaas_client.create_subscription(data)
