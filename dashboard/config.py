import os
import dotenv
import hashlib
import base64
from pathlib import Path
from cryptography.fernet import Fernet

CONFIG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CONFIG_DIR.parent
DOTENV_PATH = CONFIG_DIR / ".env"

dotenv.load_dotenv(DOTENV_PATH)


def _get_env(*keys, default=None):
    for key in keys:
        value = os.getenv(key)
        if value not in (None, ""):
            return value
    return default


def _normalize_path(value, default):
    raw_value = value or default
    return os.path.normpath(str(raw_value).replace("\x08", "\\b"))


DEFAULT_PATH_EXE_BOTAO = PROJECT_ROOT / "dist" / "botao_de_enviar.exe"
DEFAULT_PATH_RECEPTOR = PROJECT_ROOT / "dist" / "BotaoPanico_Receptor.exe"
DEFAULT_ORACLE_CLIENT_DIR = CONFIG_DIR / "modules" / "instantclient_23_7"

PATH_EXE_BOTAO = _normalize_path(
    _get_env("PATH_EXE_BOTAO", "path_exe_botao"),
    DEFAULT_PATH_EXE_BOTAO,
)
PATH_RECEPTOR = _normalize_path(
    _get_env("PATH_RECEPTOR", "path_receptor"),
    DEFAULT_PATH_RECEPTOR,
)
ORACLE_CLIENT_LIB_DIR = _normalize_path(
    _get_env("ORACLE_CLIENT_LIB_DIR", "oracle_client_lib_dir"),
    DEFAULT_ORACLE_CLIENT_DIR if DEFAULT_ORACLE_CLIENT_DIR.exists() else "",
)
DNS_SERVER = _get_env("DNS_SERVER", "dns_server", default="172.19.0.10")
DATABASE_HOST = _get_env("DATABASE_HOST", "database_host")
DATABASE_USER = _get_env("DATABASE_USER", "database_user")
DATABASE_PASSWORD = _get_env("PASSWORD", "password")
DATABASE_PORT = int(_get_env("DATABASE_PORT", "PORT", "porta", "port", default="1521"))
DATABASE_SERVICE = _get_env("DATABASE_SERVICE", "database_service")
SERVER_IP = _get_env("SERVER_IP", "server_ip")
DATABASE_SCHEMA = _get_env("DATABASE_SCHEMA", "database_schema")
DASHBOARD_PORT = int(_get_env("DASHBOARD_PORT", "dashboard_port", default="3303"))
SERVER_PORT = int(_get_env("SERVER_PORT", "server_port", default="9600"))

SECRET_KEY = _get_env("SECRET_KEY", default="change-this-secret-key")
SESSION_COOKIE_SECURE = False

SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}" if SERVER_IP else f"http://127.0.0.1:{SERVER_PORT}"

SECRET_KEY_BYTES = hashlib.sha256(SECRET_KEY.encode()).digest()
SECRET_KEY_ENCODED = base64.urlsafe_b64encode(SECRET_KEY_BYTES)
FERNET = Fernet(SECRET_KEY_ENCODED)

path_exe_botao = PATH_EXE_BOTAO
