import os
import oracledb
from config import DATABASE_HOST, DATABASE_PORT, DATABASE_SERVICE, DATABASE_USER, DATABASE_PASSWORD, DATABASE_SCHEMA, ORACLE_CLIENT_LIB_DIR

_oracle_client_initialized = False


def _init_oracle_client():
    global _oracle_client_initialized
    if _oracle_client_initialized:
        return
    if ORACLE_CLIENT_LIB_DIR and os.path.isdir(ORACLE_CLIENT_LIB_DIR):
        oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB_DIR)
    _oracle_client_initialized = True


def conectar_banco_de_dados():
    try:
        _init_oracle_client()
        dsn = oracledb.makedsn(
            host=DATABASE_HOST,
            port=DATABASE_PORT,
            service_name=DATABASE_SERVICE
        )
        conn = oracledb.connect(
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            dsn=dsn
        )
        return conn
    except oracledb.Error as e:
        print(f"Erro ao conectar ao banco de dados Oracle: {e}")
        return None


def obter_proximo_id(sequence_name):
    conn = conectar_banco_de_dados()
    if not conn:
        return None

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {DATABASE_SCHEMA}.{sequence_name}.NEXTVAL FROM DUAL")
        proximo_id = cursor.fetchone()[0]
        return proximo_id
    except Exception as e:
        print(f"Erro ao obter prÃ³ximo ID da sequence {sequence_name}: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        conn.close()
