import os
import dotenv
import hashlib
import base64
from cryptography.fernet import Fernet

path_exe_botao  = r"C:\py\BASE\botao\dist\botao_de_enviar.exe"

dotenv.load_dotenv()
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