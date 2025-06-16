import bcrypt
from functools import wraps
from flask import session, redirect, url_for
from config import FERNET
from modules.database import conectar_banco_de_dados, DATABASE_SCHEMA

def criptografar_reversivel(texto):
    if not texto:
        return None
    return FERNET.encrypt(texto.encode('utf-8')).decode('utf-8')

def descriptografar(texto_criptografado):
    if not texto_criptografado:
        return None
    return FERNET.decrypt(texto_criptografado.encode('utf-8')).decode('utf-8')

def criptografar_senha(senha):
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_senha(senha, hash_senha):
    return bcrypt.checkpw(senha.encode('utf-8'), hash_senha.encode('utf-8'))

def verificar_credenciais(usuario, senha):
    conn = conectar_banco_de_dados()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT senha 
            FROM {DATABASE_SCHEMA}.da_tbl_botao_usuario_login 
            WHERE usuario = :usuario
        """, {'usuario': usuario})
        
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if resultado:
            hash_senha = resultado[0]
            return verificar_senha(senha, hash_senha)
        
        return False
    except Exception as e:
        print(f"Erro ao verificar credenciais: {e}")
        if conn:
            conn.close()
        return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_logado' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function 