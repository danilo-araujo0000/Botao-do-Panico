#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import random
import string
import threading
from datetime import datetime
from pathlib import Path

import dotenv
import oracledb
import requests
from flask import Flask, request, jsonify

if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DOTENV_PATH = BASE_DIR / '.env'
DEFAULT_ORACLE_CLIENT_DIR = PROJECT_ROOT / 'dashboard' / 'modules' / 'instantclient_23_7'

dotenv.load_dotenv(DOTENV_PATH)


def _get_env(*keys, default=None):
    for key in keys:
        value = os.getenv(key)
        if value not in (None, ''):
            return value
    return default


database_host = _get_env('DATABASE_HOST', 'database_host')
database_user = _get_env('DATABASE_USER', 'database_user')
database_password = _get_env('PASSWORD', 'password')
database_port = int(_get_env('DATABASE_PORT', 'PORT', 'porta', 'port', default='1521'))
database_service = _get_env('DATABASE_SERVICE', 'database_service')
database_schema = _get_env('DATABASE_SCHEMA', 'database_schema')
server_port = int(_get_env('SERVER_PORT', 'server_port', default='9600'))
oracle_client_lib_dir = _get_env(
    'ORACLE_CLIENT_LIB_DIR',
    'oracle_client_lib_dir',
    default=str(DEFAULT_ORACLE_CLIENT_DIR) if DEFAULT_ORACLE_CLIENT_DIR.exists() else '',
)

_oracle_client_initialized = False


def _init_oracle_client():
    global _oracle_client_initialized
    if _oracle_client_initialized:
        return
    if oracle_client_lib_dir and os.path.isdir(oracle_client_lib_dir):
        oracledb.init_oracle_client(lib_dir=oracle_client_lib_dir)
    _oracle_client_initialized = True


app = Flask(__name__)


def gerar_combo(tamanho=6):
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choices(caracteres, k=tamanho))


@app.route('/alerta5656/enviar', methods=['POST'])
def receber_acao():
    global hostname
    global id_evento
    global request_ip
    id_evento = gerar_combo()
    request_ip = request.remote_addr
    data = request.get_json()

    if data is None:
        salvar_logs_sitema(f"Nenhum dado JSON foi recebido por {request_ip} - {id_evento}")
        return jsonify({"error": "Nenhum dado JSON foi recebido"}), 400

    if 'hostname' not in data or 'usuario' not in data or 'codigo' not in data:
        salvar_logs_sitema(f"Dados obrigatórios ausentes (hostname, usuario, codigo) por {request_ip} - {id_evento}")
        return jsonify({"error": "Dados obrigatórios ausentes (hostname, usuario, codigo)"}), 400

    hostname = data['hostname']
    usuario = data['usuario']

    nome_usuario = localizar_usuario(usuario)
    if nome_usuario is None:
        nome_usuario = usuario

    nome_sala = localizar_sala(hostname)
    if nome_sala is None:
        nome_sala = "Sala não encontrada"

    enviar_alerta(nome_usuario, nome_sala)
    salvar_logs_sitema(f"Ação recebida com sucesso por {request_ip} para o usuário {nome_usuario} na sala {nome_sala}")
    return jsonify({"message": "Ação recebida com sucesso"}), 200


@app.route('/check-health', methods=['GET'])
def check_health():
    return jsonify({"status": "ok"}), 200


def enviar_alerta(nome_usuario, nome_sala):
    salvar_logs_sitema(f"Enviando alerta do usuário {nome_usuario} da sala {nome_sala} - {id_evento}")
    lista_receptores = localizar_receptores()

    if not lista_receptores:
        salvar_logs_sitema("Nenhum receptor encontrado")
        return

    threads = []

    for receptor in lista_receptores:
        ip_receptor = receptor[0]
        thread = threading.Thread(
            target=enviar_para_receptor,
            args=(ip_receptor, nome_usuario, nome_sala)
        )
        threads.append(thread)
        thread.start()
        salvar_logs_sitema(f"Thread iniciada para receptor: {ip_receptor} - {id_evento}")

    try:
        for thread in threads:
            thread.join(timeout=30)
        salvar_logs_sitema(f"Envio massivo concluído para {len(lista_receptores)} receptores")
    except Exception as e:
        salvar_logs_sitema(f"Erro ao aguardar threads: {e}")


def enviar_para_receptor(ip_receptor, nome_usuario, nome_sala):
    hostname_chamador = hostname
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "Erro"

    try:
        response = requests.post(
            f"http://{ip_receptor}:9090/alerta5656/enviar",
            json={"sala": nome_sala, "usuario": nome_usuario, "codigo": "alerta5656"},
            timeout=4
        )

        if response.status_code == 200:
            status = "Enviado"
            salvar_logs_sitema(f"Alerta enviado com sucesso para o receptor {ip_receptor}")
        else:
            status = "Erro_HTTP"
            salvar_logs_sitema(f"Erro ao enviar alerta para o receptor {ip_receptor} - Status: {response.status_code}")

    except requests.exceptions.ConnectTimeout:
        status = "Timeout"
        salvar_logs_sitema(f"Timeout ao enviar para receptor {ip_receptor}")
    except requests.exceptions.ConnectionError as e:
        status = "Erro_Conexao"
        salvar_logs_sitema(f"Erro de conexão com receptor {ip_receptor}: {str(e)}")
    except requests.exceptions.RequestException as e:
        status = "Erro_Request"
        salvar_logs_sitema(f"Erro de requisição para receptor {ip_receptor}: {str(e)}")
    except Exception as e:
        status = "Erro_Geral"
        salvar_logs_sitema(f"Erro inesperado ao enviar para receptor {ip_receptor}: {str(e)}")

    salvar_log_alertas(ip_receptor, hostname_chamador, nome_usuario, nome_sala, data_hora, status, id_evento)


def conectar_banco_de_dados():
    try:
        _init_oracle_client()
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


def obter_proximo_id(sequence_name):
    conn = conectar_banco_de_dados()
    if not conn:
        return None

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {database_schema}.{sequence_name}.NEXTVAL FROM DUAL")
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"Erro ao obter próximo ID da sequence {sequence_name}: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        conn.close()


def salvar_log_alertas(ip_receptor, hostname_chamador, nome_usuario, nome_sala, data_hora, status, id_evento):
    try:
        novo_id = obter_proximo_id('seq_botao_log_alerta')
        if not novo_id:
            print("[ERRO] Falha ao obter ID da sequence para log de alerta")
            return

        conn = conectar_banco_de_dados()
        if conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {database_schema}.da_tbl_botao_log_alerta
                (id, ip_receptor, hostname_chamador, nome_usuario, nome_sala, data_hora, status, id_evento)
                VALUES (:id, :ip_receptor, :hostname_chamador, :nome_usuario, :nome_sala,
                        TO_TIMESTAMP(:data_hora, 'YYYY-MM-DD HH24:MI:SS'), :status, :id_evento)
            """, {
                'id': novo_id,
                'ip_receptor': ip_receptor,
                'hostname_chamador': hostname_chamador,
                'nome_usuario': nome_usuario,
                'nome_sala': nome_sala,
                'data_hora': data_hora,
                'status': status,
                'id_evento': id_evento
            })
            conn.commit()
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[ERRO] Falha ao salvar log de alerta: {str(e)}")


def localizar_usuario(usuario):
    conn = conectar_banco_de_dados()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT nome_usuario FROM {database_schema}.da_tbl_botao_usuario WHERE username = :usuario",
                {'usuario': usuario}
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if result:
                return result[0]
            return None
        except Exception as e:
            print(f"[ERRO] Falha ao localizar usuário {usuario}: {str(e)}")
            conn.close()
            return None
    return None


def localizar_sala(hostname):
    conn = conectar_banco_de_dados()
    if conn:
        query = f"SELECT nome_sala FROM {database_schema}.da_tbl_botao_sala WHERE hostname = :hostname"
        try:
            cursor = conn.cursor()
            cursor.execute(query, {'hostname': hostname.lower()})
            result = cursor.fetchone()
            if result:
                cursor.close()
                conn.close()
                return result[0]

            if hostname.upper() == hostname:
                cursor.execute(query, {'hostname': hostname.upper()})
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                if result:
                    return result[0]
                return "sala Não Encontrada"

            cursor.close()
            conn.close()
            return "sala Não Encontrada"
        except Exception as e:
            print(f"[ERRO] Falha ao localizar sala {hostname}: {str(e)}")
            conn.close()
            return "sala Não Encontrada"
    print("Erro ao conectar ao banco de dados --- localizar sala")
    return None


def localizar_receptores():
    conn = conectar_banco_de_dados()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT ip_receptor FROM {database_schema}.da_tbl_botao_receptor")
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result
        except Exception as e:
            print(f"[ERRO] Falha ao localizar receptores: {str(e)}")
            conn.close()
            return []
    return []


def salvar_logs_sitema(log):
    try:
        novo_id = obter_proximo_id('seq_botao_log_sistema')
        if not novo_id:
            print("[ERRO] Falha ao obter ID da sequence para log do sistema")
            return

        conn = conectar_banco_de_dados()
        if conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {database_schema}.da_tbl_botao_log_sistema (id, log, nivel, modulo, usuario)
                VALUES (:id, :log, :nivel, :modulo, :usuario)
            """, {
                'id': novo_id,
                'log': log,
                'nivel': 'INFO',
                'modulo': 'SERVER',
                'usuario': 'SISTEMA'
            })
            conn.commit()
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[ERRO] Falha ao salvar log do sistema: {str(e)}")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=server_port)
