import os
import dotenv
import hashlib
import base64
from cryptography.fernet import Fernet

DEFAULT_PATH_EXE_BOTAO = r"C:\py\BASE\botao\dist\botao_de_enviar.exe"


def _normalizar_caminho_env(valor, padrao):
    if not valor:
        return padrao
    return os.path.normpath(valor.replace('\x08', '\\b'))

dotenv.load_dotenv()
PATH_EXE_BOTAO = _normalizar_caminho_env(
    os.getenv('PATH_EXE_BOTAO') or os.getenv('path_exe_botao'),
    DEFAULT_PATH_EXE_BOTAO
)
path_exe_botao = PATH_EXE_BOTAO
dns_server = os.getenv('DNS_SERVER')
if dns_server is None:
    dns_server = "172.19.0.10"
DATABASE_HOST = os.getenv('DATABASE_HOST')
DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_PASSWORD = os.getenv('PASSWORD')
DATABASE_PORT = 1521
DATABASE_SERVICE = os.getenv('DATABASE_SERVICE')
SERVER_IP = os.getenv('SERVER_IP')
DATABASE_SCHEMA = os.getenv('DATABASE_SCHEMA')

SECRET_KEY = 'botao_panico_dashboard_2025_100%_atualizado'
SESSION_COOKIE_SECURE = False

SERVER_URL = f"http://{SERVER_IP}:9600"

SECRET_KEY_BYTES = hashlib.sha256(SECRET_KEY.encode()).digest()
SECRET_KEY_ENCODED = base64.urlsafe_b64encode(SECRET_KEY_BYTES)
FERNET = Fernet(SECRET_KEY_ENCODED) 
