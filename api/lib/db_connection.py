"""
Módulo de conexão com banco de dados PostgreSQL.

Fornece função global get_conn() para obter conexões com o banco.
"""

import os
import psycopg2
import psycopg2.pool
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Pool de conexões para melhor performance
connection_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None


def init_connection_pool():
    """Inicializa o pool de conexões se ainda não foi inicializado."""
    global connection_pool

    if connection_pool is None:
        try:
            connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT", "5432")
            )
            logger.info("✅ Pool de conexões PostgreSQL inicializado")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar pool de conexões: {e}")
            raise


def get_conn():
    """
    Obtém uma conexão do pool de conexões PostgreSQL.

    Returns:
        Conexão psycopg2

    Raises:
        Exception: Se não conseguir obter conexão
    """
    global connection_pool

    if connection_pool is None:
        init_connection_pool()

    try:
        conn = connection_pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"❌ Erro ao obter conexão do pool: {e}")
        raise


def release_conn(conn):
    """
    Libera uma conexão de volta para o pool.

    Args:
        conn: Conexão psycopg2 a ser liberada
    """
    global connection_pool

    if connection_pool is not None:
        try:
            connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"❌ Erro ao liberar conexão: {e}")


def close_all_connections():
    """Fecha todas as conexões do pool."""
    global connection_pool

    if connection_pool is not None:
        connection_pool.closeall()
        logger.info("✅ Todas as conexões fechadas")