import oracledb
import dotenv
import os

dotenv.load_dotenv()

database_host = os.getenv('DATABASE_HOST')
database_user = os.getenv('DATABASE_USER')
database_password = os.getenv('PASSWORD')
database_port = 1521
database_service = os.getenv('DATABASE_SERVICE')

def testar_conexao():
    conn = conectar_banco_de_dados()
    if conn:
        print("Conexão estabelecida com sucesso! - teste conexao oracle")
        conn.close()
    else:
        print("Erro ao conectar ao banco de dados")

def conectar_banco_de_dados():
    oracledb.init_oracle_client(lib_dir=os.path.join(os.path.dirname(__file__), '../dashboard/instantclient_23_7'))

    try:
        dsn = oracledb.makedsn(
            host=database_host,
            port=database_port,
            service_name=database_service
        )
        conn = oracledb.connect(
            user=database_user,
            password=database_password,
            dsn=dsn
        )
        return conn
    except oracledb.Error as e:
        print(f"Erro ao conectar ao banco de dados Oracle: {e}")
        return None




testar_conexao()
