import mysql.connector
from mysql.connector import Error, pooling
import os
import json
from dotenv import load_dotenv
from ..lib.queries import (PRIMEIRO_PILAR, SEGUNDO_PILAR, 
                         TERCEIRO_PILAR, QUARTO_PILAR, 
                         ECONVERSA_STATUS, INTEGRATORS_CONNECTED)
from ..scripts.clientes import clientes_to_dataframe
from typing import Dict, List, Optional
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import threading
import uuid
import psycopg2
from .clientes import get_conn as get_psql_conn
import time

load_dotenv()
logger = logging.getLogger(__name__)

# Connection pool global e lock para thread-safety
connection_pool = None
pool_lock = threading.Lock()

def init_connection_pool():
    """Inicializa o pool de conexões MySQL (thread-safe)."""
    global connection_pool
    
    # Double-check locking pattern para thread-safety
    if connection_pool is not None:
        return connection_pool
    
    with pool_lock:
        # Verificar novamente dentro do lock
        if connection_pool is not None:
            return connection_pool
        
        try:
            connection_pool = pooling.MySQLConnectionPool(
                pool_name="ecosys_pool",
                pool_size=7,  # Aumentado para suportar queries paralelas
                pool_reset_session=True,
                host=os.getenv('DB_HOST_ECOSYS'),
                database=os.getenv('DB_NAME_ECOSYS'),
                user=os.getenv('DB_USER_ECOSYS'),
                password=os.getenv('DB_PASSWORD_ECOSYS'),
                port=3306,
                autocommit=True,
                connect_timeout=10
            )
            logger.info("✅ Pool de conexões MySQL criado com sucesso (pool_size=7)")
            return connection_pool
        except Error as e:
            logger.error(f"❌ Erro ao criar pool de conexões: {e}")
            return None

def get_conn():
    """Obtém uma conexão do pool."""
    global connection_pool
    
    if connection_pool is None:
        connection_pool = init_connection_pool()
    
    try:
        return connection_pool.get_connection()
    except Error as e:
        logger.error(f"Erro ao obter conexão do pool: {e}")
        return None

def execute_query(conn, query):
    """Executa query e retorna DataFrame."""
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        
        df = pd.DataFrame(results)
        return df
        
    except Error as e:
        logger.error(f"Erro ao executar query: {e}")
        return None

def execute_queries_parallel(queries: List[tuple]) -> Dict[str, pd.DataFrame]:
    """
    Executa múltiplas queries em paralelo.
    
    Args:
        queries: Lista de tuplas (nome, query_sql)
    
    Returns:
        Dicionário com nome: DataFrame
    """
    results = {}
    
    def execute_single_query(name: str, query: str):
        """Executa uma única query em uma conexão separada"""
        conn = get_conn()
        if conn is None:
            logger.error(f"Falha ao obter conexão para query {name}")
            return name, None
        
        try:
            df = execute_query(conn, query)
            return name, df
        finally:
            conn.close()
    
    # Executar queries em paralelo usando ThreadPoolExecutor
    # Limita workers ao tamanho do pool para evitar esgotamento
    max_parallel_queries = min(len(queries), 7)  # Máximo de 7 queries simultâneas
    with ThreadPoolExecutor(max_workers=max_parallel_queries) as executor:
        future_to_query = {
            executor.submit(execute_single_query, name, query): name 
            for name, query in queries
        }
        
        for future in as_completed(future_to_query):
            name, df = future.result()
            if df is not None:
                results[name] = df
                logger.info(f"Query {name} executada com sucesso")
            else:
                logger.error(f"Falha ao executar query {name}")
    
    return results


def fetch_all_data() -> Dict[str, pd.DataFrame]:
    """
    Busca todos os dados necessários executando queries em paralelo.
    
    Returns:
        Dict com DataFrames: tenants, primeiro_pilar, segundo_pilar, etc.
    """
    queries = [
        ("tenants", "SELECT id, name, cnpj, slug FROM tenants;"),
        ("primeiro_pilar", PRIMEIRO_PILAR),
        ("segundo_pilar", SEGUNDO_PILAR),
        ("terceiro_pilar", TERCEIRO_PILAR),
        ("quarto_pilar", QUARTO_PILAR),
        ("econversa", ECONVERSA_STATUS),
        ("integrators", INTEGRATORS_CONNECTED)
    ]
    
    logger.info("Iniciando execução paralela de queries...")
    dfs = execute_queries_parallel(queries)
    
    # Verificar se todas as queries foram bem-sucedidas
    required_keys = ["tenants", "primeiro_pilar", "segundo_pilar", "terceiro_pilar", "quarto_pilar"]
    if not all(key in dfs for key in required_keys):
        raise Exception("Falha ao executar queries necessárias")
    
    logger.info("Queries executadas com sucesso")
    return dfs


def convert_numeric_columns(dataframes: List[pd.DataFrame]) -> None:
    """
    Converte colunas numéricas para o tipo correto.
    Modifica os DataFrames in-place.
    
    Args:
        dataframes: Lista de DataFrames para converter
    """
    numeric_cols_float = [
        'score_engajamento', 'score_movimentacao_estoque', 'score_crm', 'score_adoption',
        'qntd_acessos_30d', 'dias_desde_ultimo_acesso', 'estoque_total', 'qntd_entradas_30d',
        'dias_desde_ultima_entrada', 'qntd_saidas_30d', 'dias_desde_ultima_saida',
        'qntd_leads_30d', 'dias_desde_ultimo_lead', 'usuarios_ativos_30d'
    ]
    
    for df in dataframes:
        for col in numeric_cols_float:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce', downcast='float')


def merge_pillar_data(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Faz o merge de todos os pilares e dados complementares.
    
    Args:
        dfs: Dicionário com DataFrames dos pilares
    
    Returns:
        DataFrame com todos os dados mesclados
    """
    df_tenants = dfs["tenants"]
    df_primeiro_pilar = dfs["primeiro_pilar"]
    df_segundo_pilar = dfs["segundo_pilar"]
    df_terceiro_pilar = dfs["terceiro_pilar"]
    df_quarto_pilar = dfs["quarto_pilar"]
    df_econversa = dfs.get("econversa", pd.DataFrame())
    df_integrators = dfs.get("integrators", pd.DataFrame())
    
    # Converter colunas numéricas antes dos merges
    convert_numeric_columns([df_primeiro_pilar, df_segundo_pilar, df_terceiro_pilar, df_quarto_pilar])
    
    logger.info("Iniciando merge dos pilares...")
    
    # Merge dos pilares principais
    df_fusao = df_tenants.merge(
        df_primeiro_pilar,
        left_on='id',
        right_on='tenant_id',
        how='left',
        suffixes=('', '_p1'),
        copy=False
    )
    
    df_fusao = df_fusao.merge(
        df_segundo_pilar,
        left_on='id',
        right_on='tenant_id',
        how='left',
        suffixes=('', '_p2'),
        copy=False
    )
    
    df_fusao = df_fusao.merge(
        df_terceiro_pilar,
        left_on='id',
        right_on='tenant_id',
        how='left',
        suffixes=('', '_p3'),
        copy=False
    )
    
    df_fusao = df_fusao.merge(
        df_quarto_pilar,
        left_on='id',
        right_on='tenant_id',
        how='left',
        suffixes=('', '_p4'),
        copy=False
    )
    
    # Merge com dados complementares
    if not df_econversa.empty:
        df_fusao = df_fusao.merge(
            df_econversa,
            left_on='id',
            right_on='id',
            how='left',
            copy=False
        )
    
    if not df_integrators.empty:
        df_fusao = df_fusao.merge(
            df_integrators,
            left_on='id',
            right_on='tenant_id',
            how='left',
            copy=False
        )
    
    logger.info("Merge concluído com sucesso")
    return df_fusao


def process_integration_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processa dados de integrações (eConversa e integradores).
    
    Args:
        df: DataFrame com dados brutos
    
    Returns:
        DataFrame com dados de integração processados
    """
    # Converter econversa_connected para booleano
    if 'econversa_connected' in df.columns:
        df['econversa_connected'] = (
            df['econversa_connected']
            .fillna('connecting')
            .str.lower() == 'open'
        )
    else:
        df['econversa_connected'] = False
    
    # Converter string de integradores para lista
    if 'integrators_connected' in df.columns:
        df['integrators_connected'] = df['integrators_connected'].fillna('').str.split(', ')
        df['integrators_connected'] = df['integrators_connected'].apply(
            lambda x: [i for i in x if i] if isinstance(x, list) else []
        )
    else:
        df['integrators_connected'] = [[] for _ in range(len(df))]
    
    return df


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa o DataFrame removendo colunas duplicadas e renomeando.
    
    Args:
        df: DataFrame para limpar
    
    Returns:
        DataFrame limpo
    """
    # Renomear id para tenant_id
    if 'id' in df.columns:
        df = df.rename(columns={'id': 'tenant_id'})
    
    # Remover colunas duplicadas
    cols_to_drop = [col for col in df.columns 
                    if col.startswith('tenant_id_') or 
                    (col != 'tenant_id' and 'tenant_id' in col)]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
    
    # Remover colunas duplicadas por nome
    df = df.loc[:, ~df.columns.duplicated()]
    
    return df


def calculate_total_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o score total ponderado baseado nos 4 pilares.
    
    Args:
        df: DataFrame com scores dos pilares
    
    Returns:
        DataFrame com score_total calculado
    """
    WEIGHTS = {
        'score_engajamento': 0.35,
        'score_movimentacao_estoque': 0.35,
        'score_crm': 0.20,
        'score_adoption': 0.10
    }
    
    # Garantir que colunas de score existam e sejam numéricas
    for col in WEIGHTS.keys():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    
    # Calcular score total de forma vetorizada
    df['score_total'] = sum(
        df[col] * weight 
        for col, weight in WEIGHTS.items() 
        if col in df.columns
    )
    
    logger.info("Score total calculado com sucesso")
    return df


def select_final_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Seleciona e reordena as colunas finais do DataFrame.
    
    Args:
        df: DataFrame com todas as colunas
    
    Returns:
        DataFrame com colunas selecionadas e ordenadas
    """
    colunas_finais = [
        'tenant_id', 'slug', 'name', 'cnpj', 'qntd_acessos_30d',
        'dias_desde_ultimo_acesso', 'usuarios_ativos_30d', 'tipo_equipe', 'score_engajamento',
        'estoque_total', 'porte_loja', 'qntd_entradas_30d', 'dias_desde_ultima_entrada',
        'qntd_saidas_30d', 'dias_desde_ultima_saida',
        'score_movimentacao_estoque', 'qntd_leads_30d',
        'dias_desde_ultimo_lead', 'score_crm',
        'econversa_connected', 'integrators_connected', 'ads_status', 'reports_status',
        'econversa_status', 'contracts_status', 'score_adoption', 'score_total'
    ]
    
    # Manter apenas as colunas que existem
    colunas_existentes = [col for col in colunas_finais if col in df.columns]
    return df[colunas_existentes]


def filter_active_clients(
    df: pd.DataFrame,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
) -> pd.DataFrame:
    """
    Filtra apenas clientes ativos baseado na lista de clientes.
    
    Considera clientes que aderiram OU deram churn no período.
    
    Args:
        df: DataFrame com todos os dados
        data_inicio: Data inicial para filtro (formato: YYYY-MM-DD)
        data_fim: Data final para filtro (formato: YYYY-MM-DD)
    
    Returns:
        DataFrame filtrado com apenas clientes ativos (ou que deram churn) no período
    """
    clientes = clientes_to_dataframe(data_inicio, data_fim)
    
    # Conversões de tipo em batch
    df['cnpj'] = pd.to_numeric(df['cnpj'], errors='coerce').fillna(0).astype('int64')
    clientes['cnpj'] = pd.to_numeric(clientes['cnpj'], errors='coerce').fillna(0).astype('int64')
    
    # Filtrar e limpar dados
    df = df[df['cnpj'].isin(clientes['cnpj'])]
    # Logar clientes com tenant_id nulo antes de dropá-los
    null_tenants = df[df['tenant_id'].isna()]
    with open('null_tenants_log.json', 'w', encoding='utf-8') as f:
        json.dump(null_tenants[['cnpj', 'name', 'slug']].to_dict('records'), f, indent=2)
    if not null_tenants.empty:
        null_tenants_data = null_tenants[['cnpj', 'name', 'slug']].to_dict('records')
        logger.warning(f"Clientes removidos por tenant_id nulo: {json.dumps(null_tenants_data, indent=2)}")
    
    df = df.dropna(subset=['tenant_id'])
    df.sort_values(by='score_total', ascending=False, inplace=True)
    
    # Reordenar colunas
    colunas_ordenadas = ['tenant_id', 'slug'] + [
        col for col in df.columns if col not in ['tenant_id', 'slug']
    ]
    df = df[colunas_ordenadas]
    
    return df


def categorize_clients(df: pd.DataFrame) -> pd.DataFrame:
    """
    Categoriza clientes baseado no score total.
    
    Args:
        df: DataFrame com score_total
    
    Returns:
        DataFrame com coluna 'categoria' adicionada
    """
    def categorizar_cliente(score):
        if pd.isna(score) or score <= 0.3:
            return 'Crítico'
        elif score <= 0.6:
            return 'Normal'
        elif score <= 0.8:
            return 'Saudável'
        else:
            return 'Campeão'
    
    df['categoria'] = df['score_total'].apply(categorizar_cliente)
    logger.info(f"Distribuição das categorias:\n{df['categoria'].value_counts()}")
    
    return df


def convert_column_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte tipos de colunas para os formatos finais (int, float).
    
    Args:
        df: DataFrame para converter
    
    Returns:
        DataFrame com tipos convertidos
    """
    int_columns = [
        'cnpj', 'qntd_acessos_30d', 'dias_desde_ultimo_acesso',
        'qntd_entradas_30d', 'dias_desde_ultima_entrada',
        'qntd_saidas_30d', 'dias_desde_ultima_saida',
        'qntd_leads_30d', 'dias_desde_ultimo_lead'
    ]
    
    float_columns = [
        'score_total', 'score_engajamento', 'score_movimentacao_estoque',
        'score_crm', 'score_adoption'
    ]
    
    # Aplicar conversões de tipo
    for col in int_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int64')
    
    for col in float_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').round(2)
    
    return df


def dataframe_to_dict(df: pd.DataFrame) -> Dict:
    """
    Converte DataFrame para dicionário estruturado indexado por slug.
    
    Args:
        df: DataFrame processado
    
    Returns:
        Dicionário com dados estruturados por slug
    """
    resultado = {}
    
    # Usar itertuples para melhor performance
    for row in df.itertuples(index=False):
        if pd.notna(row.slug):
            resultado[row.slug] = {
                'tenant_id': str(row.tenant_id) if pd.notna(row.tenant_id) else None,
                'name': row.name if pd.notna(row.name) else None,
                'cnpj': int(row.cnpj) if pd.notna(row.cnpj) else 0,
                'slug': row.slug,
                'scores': {
                    'engajamento': round(float(row.score_engajamento), 2) if pd.notna(row.score_engajamento) else 0.0,
                    'adocao': round(float(row.score_adoption), 2) if pd.notna(row.score_adoption) else 0.0,
                    'estoque': round(float(row.score_movimentacao_estoque), 2) if pd.notna(row.score_movimentacao_estoque) else 0.0,
                    'crm': round(float(row.score_crm), 2) if pd.notna(row.score_crm) else 0.0,
                    'total': round(float(row.score_total), 2) if pd.notna(row.score_total) else 0.0
                },
                'adoption': {
                    'econversa_status': round(float(row.econversa_status), 2) if hasattr(row, 'econversa_status') and pd.notna(row.econversa_status) else 0.0,
                    'ads_status': round(float(row.ads_status), 2) if hasattr(row, 'ads_status') and pd.notna(row.ads_status) else 0.0,
                    'reports_status': round(float(row.reports_status), 2) if hasattr(row, 'reports_status') and pd.notna(row.reports_status) else 0.0,
                    'contracts_status': round(float(row.contracts_status), 2) if hasattr(row, 'contracts_status') and pd.notna(row.contracts_status) else 0.0
                },
                'integrations': {
                    'econversa_connected': bool(row.econversa_connected) if hasattr(row, 'econversa_connected') and pd.notna(row.econversa_connected) else False,
                    'integrators_connected': row.integrators_connected if hasattr(row, 'integrators_connected') else []
                },
                'metrics': {
                    'acessos': {
                        'quantidade_30d': int(row.qntd_acessos_30d) if pd.notna(row.qntd_acessos_30d) else 0,
                        'dias_ultimo_acesso': int(row.dias_desde_ultimo_acesso) if pd.notna(row.dias_desde_ultimo_acesso) else 9999,
                        'usuarios_ativos_30d': int(row.usuarios_ativos_30d) if pd.notna(row.usuarios_ativos_30d) else 0,
                        'tipo_equipe': str(row.tipo_equipe) if hasattr(row, 'tipo_equipe') and pd.notna(row.tipo_equipe) else None
                    },
                    'estoque': {
                        'veiculos_em_estoque': int(row.estoque_total) if pd.notna(row.estoque_total) else 0,
                        'porte_loja': str(row.porte_loja) if pd.notna(row.porte_loja) else None
                    },
                    'entradas': {
                        'quantidade_30d': int(row.qntd_entradas_30d) if pd.notna(row.qntd_entradas_30d) else 0,
                        'dias_ultima_entrada': int(row.dias_desde_ultima_entrada) if pd.notna(row.dias_desde_ultima_entrada) else 9999
                    },
                    'saidas': {
                        'quantidade_30d': int(row.qntd_saidas_30d) if pd.notna(row.qntd_saidas_30d) else 0,
                        'dias_ultima_saida': int(row.dias_desde_ultima_saida) if pd.notna(row.dias_desde_ultima_saida) else 9999
                    },
                    'leads': {
                        'quantidade_30d': int(row.qntd_leads_30d) if pd.notna(row.qntd_leads_30d) else 0,
                        'dias_ultimo_lead': int(row.dias_desde_ultimo_lead) if pd.notna(row.dias_desde_ultimo_lead) else 9999
                    }
                },
                'categoria': str(row.categoria)
            }
    
    logger.info(f"Processamento concluído. {len(resultado)} clientes processados.")
    return resultado

def store_health_scores_in_db(health_scores: Dict):
    """
    Armazena os health scores no banco de dados PostgreSQL.
    
    Args:
        health_scores: Dicionário com health scores por slug
    """
    conn = None
    try:
        conn = get_psql_conn()
        cursor = conn.cursor()
        
        last_update_query = """
            SELECT TO_CHAR(MAX(snapshot_date), 'YYYY-MM-DD') FROM health_scores_history;
        """
        cursor.execute(last_update_query)
        last_update = cursor.fetchone()[0]
        
        if last_update == time.strftime('%Y-%m-%d'):
            logger.info("Health scores já atualizados hoje. Nenhuma ação necessária.")
            return
        
        # Preparar dados em batch para inserção otimizada
        snapshot_date = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        values_list = []
        
        for slug, data in health_scores.items():
            snapshot_id = str(uuid.uuid4())
            tenant_id = data['tenant_id']
            score_total = data['scores']['total']
            score_engajamento = data['scores']['engajamento']
            score_movimentacao_estoque = data['scores']['estoque']
            score_crm = data['scores']['crm']
            score_adoption = data['scores']['adocao']
            categoria = data['categoria']
            
            values_list.append((
                snapshot_id, tenant_id, slug, score_total, score_engajamento,
                score_movimentacao_estoque, score_crm, score_adoption, categoria, snapshot_date
            ))
        
        # Batch insert usando mogrify para melhor performance
        if values_list:
            args_str = ','.join(
                cursor.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", x).decode('utf-8') 
                for x in values_list
            )
            
            query = f"""
                INSERT INTO health_scores_history (
                    id, tenant_id, slug, score_total, score_engajamento, 
                    score_movimentacao_estoque, score_crm, score_adoption, 
                    categoria, snapshot_date
                )
                VALUES {args_str}
                ON CONFLICT (id) DO UPDATE
                SET 
                    tenant_id = EXCLUDED.tenant_id,
                    score_total = EXCLUDED.score_total,
                    score_engajamento = EXCLUDED.score_engajamento,
                    score_movimentacao_estoque = EXCLUDED.score_movimentacao_estoque,
                    score_crm = EXCLUDED.score_crm,
                    score_adoption = EXCLUDED.score_adoption,
                    categoria = EXCLUDED.categoria,
                    snapshot_date = EXCLUDED.snapshot_date,
                    created_at = NOW();
            """
            cursor.execute(query)
            conn.commit()
            logger.info(f"✅ Batch insert de {len(values_list)} registros concluído")
        logger.info("Health scores armazenados com sucesso no banco de dados.")
        
    except Exception as e:
        logger.error(f"Erro ao armazenar health scores no banco: {e}")
        
    finally:
        if conn:
            conn.close()

def merge_dataframes(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """
    Orquestra todo o processo de cálculo de health scores.
    
    Filtra por período considerando tanto adesões quanto churns.
    
    Args:
        data_inicio: Data inicial para filtro (formato: YYYY-MM-DD)
        data_fim: Data final para filtro (formato: YYYY-MM-DD)
    
    Pipeline:
    1. Busca dados (queries paralelas)
    2. Merge dos pilares
    3. Processa integrações
    4. Calcula score total
    5. Categoriza clientes
    6. Converte para dicionário
    
    Returns:
        Dict com health scores indexados por slug para clientes que:
        - Aderiram no período (data_adesao) OU
        - Deram churn no período (data_cancelamento)
    """
    # 1. Buscar todos os dados
    dfs = fetch_all_data()
    
    # 2. Fazer merge de todos os pilares
    df_fusao = merge_pillar_data(dfs)
    
    # 3. Processar dados de integrações
    df_fusao = process_integration_data(df_fusao)
    
    # 4. Limpar DataFrame
    df_fusao = clean_dataframe(df_fusao)
    
    # 5. Calcular score total
    df_fusao = calculate_total_score(df_fusao)
    
    # 6. Selecionar colunas finais
    df_fusao = select_final_columns(df_fusao)
    
    # 7. Filtrar clientes do período (adesões OU churns)
    df_fusao = filter_active_clients(df_fusao, data_inicio, data_fim)
    
    # 8. Categorizar clientes
    df_fusao = categorize_clients(df_fusao)
    
    # 9. Converter tipos de colunas
    df_fusao = convert_column_types(df_fusao)
    
    # 10. Converter para dicionário estruturado
    resultado = dataframe_to_dict(df_fusao)
    
    store_health_scores_in_db(resultado)
    
    return resultado

if __name__ == "__main__":
    resultado = merge_dataframes()
    print("\nProcessamento concluído.")
    
    try:
        # Reformatar com indentação e codificação adequada
        formatted_json = json.dumps(
            resultado, 
            indent=2,
            ensure_ascii=False,
            sort_keys=False
        )
        
        # Imprimir JSON formatado
        print("\nResultados formatados:")
        print(formatted_json)
        
        # Salvar o JSON formatado em um arquivo
        with open('score_saude_clientes.json', 'w', encoding='utf-8') as f:
            f.write(formatted_json)
        print("\nJSON formatado salvo em 'score_saude_clientes.json'")
            
    except (json.JSONDecodeError, TypeError) as e:
        print(f"\nErro ao formatar JSON: {e}")