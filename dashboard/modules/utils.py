import requests
from config import SERVER_URL

def verificar_status_servidor():
    try:
        response = requests.get(f"{SERVER_URL}/check-health", timeout=5)
        return response.status_code == 200
    except:
        return False 