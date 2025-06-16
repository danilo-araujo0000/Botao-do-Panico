import oracledb
import os
from config import *

oracledb.init_oracle_client(os.path.join(os.path.dirname(__file__), 'instantclient_23_7'))

def conectar_banco_de_dados():
    try:
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
    
    try:
        print(f"SELECT {DATABASE_SCHEMA}.{sequence_name}.NEXTVAL FROM DUAL")
        print(DATABASE_SCHEMA)
        print(sequence_name)
        cursor = conn.cursor()
        cursor.execute(f"SELECT {DATABASE_SCHEMA}.{sequence_name}.NEXTVAL FROM DUAL")
        proximo_id = cursor.fetchone()[0]
        cursor.close()
        
        return proximo_id
    except Exception as e:
        print(f"Erro ao obter próximo ID da sequence {sequence_name}: {e}")
        if conn:
            cursor.close()
        return None 