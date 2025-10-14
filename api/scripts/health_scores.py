import mysql.connector
from mysql.connector import Error
import os
import json
from dotenv import load_dotenv
from ..lib.queries import (PRIMEIRO_PILAR, SEGUNDO_PILAR, 
                         TERCEIRO_PILAR, QUARTO_PILAR, 
                         ECONVERSA_STATUS, INTEGRATORS_CONNECTED)
from ..scripts.clientes import clientes_to_dataframe
from typing import Dict
import pandas as pd

load_dotenv()

def get_conn():
    """Tenta conectar a um BD MySQL remoto."""
    
    HOST_REMOTO = os.getenv('DB_HOST_ECOSYS') 
    USUARIO = os.getenv('DB_USER_ECOSYS')
    SENHA = os.getenv('DB_PASSWORD_ECOSYS')
    BD_NOME = os.getenv('DB_NAME_ECOSYS')

    try:
        conn = mysql.connector.connect(
            host=HOST_REMOTO,
            database=BD_NOME,
            user=USUARIO,
            password=SENHA,
            port=3306 # Mantenha a porta padrão, a menos que o servidor use outra
        )
        return conn
    except Error as e:
        print(f"❌ Falha na conexão remota ao MySQL:")
        print(f"   Detalhe do Erro: {e}")
        # Dica: O erro mais comum aqui é "Can't connect to MySQL server on '...' (111)" 
        # que geralmente indica um problema de Firewall ou Bind-Address.
        return None

def execute_query(conn, query):
    """Executa a query do primeiro pilar que calcula o score de engajamento."""
    try:
        cursor = conn.cursor(dictionary=True)  # Retorna resultados como dicionários
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        
        # Converter para um formato mais legível
        import pandas as pd
        df = pd.DataFrame(results)
        
        return df
        
    except Error as e:
        print(f"❌ Erro ao executar query do primeiro pilar:")
        print(f"   Detalhe: {e}")
        return None

def merge_dataframes():
    with get_conn() as conn:
        df_tenants = execute_query(conn, "SELECT id, name, cnpj, slug FROM tenants;")
        df_primeiro_pilar = execute_query(conn, PRIMEIRO_PILAR)
        df_segundo_pilar = execute_query(conn, SEGUNDO_PILAR)
        df_terceiro_pilar = execute_query(conn, TERCEIRO_PILAR)
        df_quarto_pilar = execute_query(conn, QUARTO_PILAR)
        
        # Buscar status do eConversa
        df_econversa = execute_query(conn, ECONVERSA_STATUS)
        
        # Buscar integradores conectados
        df_integrators = execute_query(conn, INTEGRATORS_CONNECTED)
        
        # Fechar a conexão ao final
        conn.close()
        print("\nConexão fechada.")
    
    # Converter os scores e valores numéricos para float antes dos merges
    numeric_columns = {
        'score_engajamento': float,
        'score_movimentacao_estoque': float,
        'score_crm': float,
        'score_adoption': float,
        'qntd_acessos_30d': float,
        'dias_desde_ultimo_acesso': float,
        'qntd_entradas_30d': float,
        'dias_desde_ultima_entrada': float,
        'qntd_saidas_30d': float,
        'dias_desde_ultima_saida': float,
        'qntd_leads_30d': float,
        'dias_desde_ultimo_lead': float
    }
    
    for df in [df_primeiro_pilar, df_segundo_pilar, df_terceiro_pilar, df_quarto_pilar]:
        for col, dtype in numeric_columns.items():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(dtype)
    
    # Primeiro merge com df_primeiro_pilar
    df_fusao = df_tenants.merge(
        df_primeiro_pilar,
        left_on='id',
        right_on='tenant_id',
        how='left',
        suffixes=('', '_p1')
    )
    
    # Merge com os demais pilares
    # Segundo Pilar - Score de Movimentação
    df_fusao = df_fusao.merge(
        df_segundo_pilar,
        left_on='id',
        right_on='tenant_id',
        how='left',
        suffixes=('', '_p2')
    )
    
    # Terceiro Pilar - Score CRM
    df_fusao = df_fusao.merge(
        df_terceiro_pilar,
        left_on='id',
        right_on='tenant_id',
        how='left',
        suffixes=('', '_p3')
    )
    
    # Quarto Pilar - Score Adoption
    df_fusao = df_fusao.merge(
        df_quarto_pilar,
        left_on='id',
        right_on='tenant_id',
        how='left',
        suffixes=('', '_p4')
    )
    
    # Merge com status do eConversa
    df_fusao = df_fusao.merge(
        df_econversa,
        left_on='id',
        right_on='id',
        how='left'
    )
    
    # Merge com integradores conectados
    df_fusao = df_fusao.merge(
        df_integrators,
        left_on='id',
        right_on='tenant_id',
        how='left'
    )
    
    # Converter status_econversa para booleano
    df_fusao['econversa_status'] = df_fusao['status_econversa'].fillna('connecting').apply(
        lambda x: True if x.lower() == 'open' else False
    )
    
    # Converter string de integradores para lista
    df_fusao['integrators_connected'] = df_fusao['integrators_connected'].fillna('').apply(
        lambda x: x.split(', ') if x else []
    )
    
    # Renomear id para tenant_id
    df_fusao = df_fusao.rename(columns={'id': 'tenant_id'})
    
    # Remover colunas tenant_id duplicadas
    tenant_id_cols = [col for col in df_fusao.columns if col.startswith('tenant_id_') or (col != 'tenant_id' and 'tenant_id' in col)]
    if tenant_id_cols:
        df_fusao = df_fusao.drop(columns=tenant_id_cols)
        
    # 1. Defina os pesos para cada pilar (a soma dos pesos deve ser 1.0)
    # Os pesos podem ser ajustados conforme sua estratégia.
    WEIGHTS = {
        'score_engajamento': 0.30,      # Peso Aumentado
        'score_movimentacao_estoque': 0.30, # Peso Aumentado
        'score_crm': 0.20,
        'score_adoption': 0.20
    }

    # 2. Converter colunas de score para float
    score_columns = list(WEIGHTS.keys())
    for col in score_columns:
        if col in df_fusao.columns:
            df_fusao[col] = df_fusao[col].astype(float)

    # 3. Inicialize as colunas temporárias
    df_fusao['score_total_ponderado'] = 0.0
    df_fusao['peso_total_existente'] = 0.0

    # 4. Itere sobre os pilares para calcular o score ponderado
    for score_col, weight in WEIGHTS.items():
        if score_col in df_fusao.columns:
            # Converte a coluna para float se ainda não estiver
            df_fusao[score_col] = pd.to_numeric(df_fusao[score_col], errors='coerce')
            
            # Adiciona o produto do Score * Peso ao numerador
            df_fusao['score_total_ponderado'] += df_fusao[score_col].fillna(0.0) * float(weight)
            
            # Adiciona o Peso ao denominador (somente se a coluna existir)
            df_fusao['peso_total_existente'] += float(weight)

    # 4. Calcule o score total final (Média Ponderada)
    # Score Total = (Soma dos Scores Ponderados) / (Soma dos Pesos Existentes)
    # Isso garante que o score final seja normalizado para a escala de 0 a 1.
    # Onde o 'peso_total_existente' for 0 (nenhum score existe), o resultado será NaN (Not a Number),
    # o que é o comportamento correto para dados incompletos.
    df_fusao['score_total'] = df_fusao['score_total_ponderado'] / df_fusao['peso_total_existente']

    # 5. Limpeza de colunas temporárias (Opcional, mas recomendado)
    df_fusao = df_fusao.drop(columns=['score_total_ponderado', 'peso_total_existente'], errors='ignore')

    df_cols = df_fusao.columns.tolist()
    print("\nColunas após cálculo do score total:")
    print(df_cols)
    # Selecionar e reordenar as colunas finais
    colunas_finais = ['tenant_id', 'slug', 'name', 'cnpj', 'qntd_acessos_30d',
                      'dias_desde_ultimo_acesso', 'score_engajamento',
                      'qntd_entradas_30d', 'dias_desde_ultima_entrada',
                      'qntd_saidas_30d', 'dias_desde_ultima_saida',
                      'score_movimentacao_estoque', 'qntd_leads_30d',
                      'dias_desde_ultimo_lead', 'score_crm',
                      'econversa_status', 'ads_status', 'reports_status',
                      'contracts_status', 'score_adoption', 'score_total']
    
    # Manter apenas as colunas que existem no DataFrame
    colunas_existentes = [col for col in colunas_finais if col in df_fusao.columns]
    df_fusao = df_fusao[colunas_existentes]

    clientes = clientes_to_dataframe()
    
    # Padronizar CNPJs convertendo para inteiro
    df_fusao['cnpj'] = pd.to_numeric(df_fusao['cnpj'], errors='coerce').fillna(0).astype('int64')
    clientes['cnpj'] = pd.to_numeric(clientes['cnpj'], errors='coerce').fillna(0).astype('int64')
    
    df_fusao = df_fusao[df_fusao['cnpj'].isin(clientes['cnpj'])]
    df_fusao = df_fusao.dropna(subset=['tenant_id'])
    df_fusao.sort_values(by='score_total', ascending=False, inplace=True)
    
    # Verificar e remover colunas duplicadas
    df_fusao = df_fusao.loc[:, ~df_fusao.columns.duplicated()]
    
    # Reordenar as colunas para colocar slug logo após o tenant_id
    colunas_ordenadas = ['tenant_id', 'slug'] + [col for col in df_fusao.columns if col not in ['tenant_id', 'slug']]
    df_fusao = df_fusao[colunas_ordenadas]
    
    # Categorização dos clientes baseada no score total
    def categorizar_cliente(score):
        if pd.isna(score) or score == 0:
            return 'Crítico'
        elif score <= 0.3:
            return 'Crítico'
        elif score <= 0.6:
            return 'Normal'
        elif score <= 0.8:
            return 'Saudável'
        else:
            return 'Campeão'
    
    # Aplicar a categorização usando apply
    df_fusao['categoria'] = df_fusao['score_total'].apply(categorizar_cliente)

    # Salvar em Excel
    try:
        df_fusao.to_excel('score_saude_clientes.xlsx', index=False)
        print("\nDados salvos em 'score_saude_clientes.xlsx'")
    except Exception as e:
        print(f"\nErro ao salvar arquivo Excel: {e}")
    
    # Imprimir distribuição das categorias
    print("\nDistribuição das categorias:")
    print(df_fusao['categoria'].value_counts())
    
    # Função para converter valores para o formato correto
    def convert_to_serializable(obj):
        from decimal import Decimal
        
        # Colunas que devem ser inteiros
        int_columns = [
            'cnpj', 'qntd_acessos_30d', 'dias_desde_ultimo_acesso',
            'qntd_entradas_30d', 'dias_desde_ultima_entrada',
            'qntd_saidas_30d', 'dias_desde_ultima_saida',
            'qntd_leads_30d', 'dias_desde_ultimo_lead'
        ]
        
        # Colunas que devem ser float com 2 casas decimais
        float_columns = [
            'score_engajamento', 'score_movimentacao_estoque',
            'score_crm', 'score_adoption', 'score_total',
            'econversa_status', 'ads_status', 'reports_status',
            'contracts_status'
        ]
        
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k in int_columns and pd.notna(v):
                    # Converter para inteiro
                    try:
                        result[k] = int(float(v))
                    except (ValueError, TypeError):
                        result[k] = v
                elif k in float_columns and pd.notna(v):
                    # Arredondar para 2 casas decimais
                    try:
                        result[k] = round(float(v), 2)
                    except (ValueError, TypeError):
                        result[k] = v
                else:
                    result[k] = convert_to_serializable(v)
            return result
        elif isinstance(obj, (list, tuple)):
            return [convert_to_serializable(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        elif pd.isna(obj) or pd.isnull(obj):
            return None
        elif isinstance(obj, pd.Series):
            return convert_to_serializable(obj.to_dict())
        else:
            return obj

    # Converter colunas para os tipos apropriados
    float_columns = [
        'score_total', 'score_engajamento', 'score_movimentacao_estoque',
        'score_crm', 'score_adoption', 'econversa_status', 'ads_status',
        'reports_status', 'contracts_status'
    ]
    
    int_columns = [
        'qntd_acessos_30d', 'dias_desde_ultimo_acesso',
        'qntd_entradas_30d', 'dias_desde_ultima_entrada',
        'qntd_saidas_30d', 'dias_desde_ultima_saida',
        'qntd_leads_30d', 'dias_desde_ultimo_lead'
    ]
    
    # Converter para float
    for col in float_columns:
        if col in df_fusao.columns:
            df_fusao[col] = pd.to_numeric(df_fusao[col], errors='coerce')
            
    # Converter para int
    for col in int_columns:
        if col in df_fusao.columns:
            df_fusao[col] = pd.to_numeric(df_fusao[col], errors='coerce').fillna(0).astype('int64')

    # Converter DataFrame para dicionário usando o slug como chave
    resultado = {}
    for _, row in df_fusao.iterrows():
        if pd.notna(row['slug']):
            dados_cliente = row.to_dict()
            dados_cliente = convert_to_serializable(dados_cliente)
            slug = dados_cliente['slug']
            
            # Organizar dados em uma estrutura mais clara
            resultado[slug] = {
                'tenant_id': dados_cliente['tenant_id'],
                'name': dados_cliente['name'],
                'cnpj': dados_cliente['cnpj'],
                'slug': dados_cliente['slug'],
                'scores': {
                    'ticket': dados_cliente['score_engajamento'],
                    'adoption': dados_cliente['score_adoption'],
                    'automation': dados_cliente['score_movimentacao_estoque'],
                    'nps': dados_cliente['score_crm'],
                    'total': dados_cliente['score_total']
                },
                'integrations': {
                    'econversa_status': bool(dados_cliente.get('econversa_status', False)),
                    'integrators_connected': dados_cliente.get('integrators_connected', [])
                },
                'metrics': {
                    'acessos': {
                        'quantidade_30d': dados_cliente['qntd_acessos_30d'],
                        'dias_ultimo_acesso': dados_cliente['dias_desde_ultimo_acesso']
                    },
                    'entradas': {
                        'quantidade_30d': dados_cliente['qntd_entradas_30d'],
                        'dias_ultima_entrada': dados_cliente['dias_desde_ultima_entrada']
                    },
                    'saidas': {
                        'quantidade_30d': dados_cliente['qntd_saidas_30d'],
                        'dias_ultima_saida': dados_cliente['dias_desde_ultima_saida']
                    },
                    'leads': {
                        'quantidade_30d': dados_cliente['qntd_leads_30d'],
                        'dias_ultimo_lead': dados_cliente['dias_desde_ultimo_lead']
                    }
                },
                'categoria': dados_cliente['categoria']
            }
    
    return json.dumps(resultado, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    json_str = merge_dataframes()
    print("\nProcessamento concluído.")
    
    try:
        # Converter string JSON para objeto Python
        json_data = json.loads(json_str)
        
        # Reformatar com indentação e codificação adequada
        formatted_json = json.dumps(
            json_data, 
            indent=2,             # Indentação de 2 espaços
            ensure_ascii=False,   # Permitir caracteres não-ASCII
            sort_keys=False      # Manter ordem original das chaves
        )
        
        # Imprimir JSON formatado
        print("\nResultados formatados:")
        print(formatted_json)
        
        # Opcionalmente, salvar o JSON formatado em um arquivo
        with open('score_saude_clientes.json', 'w', encoding='utf-8') as f:
            f.write(formatted_json)
        print("\nJSON formatado salvo em 'score_saude_clientes.json'")
            
    except json.JSONDecodeError as e:
        print(f"\nErro ao formatar JSON: {e}")