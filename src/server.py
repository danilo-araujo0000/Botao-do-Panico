#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from datetime import datetime
import random
import string
from flask import Flask, request, jsonify
import oracledb
import requests
import threading
import dotenv
import json



dotenv.load_dotenv()
database_host = os.getenv('DATABASE_HOST')
database_user = os.getenv('DATABASE_USER')
database_password = os.getenv('PASSWORD')
database_port = os.getenv('PORT')
database_service = os.getenv('DATABASE_SERVICE')
database_schema = os.getenv('DATABASE_SCHEMA')
dns_server = os.getenv('DNS_SERVER')
oracledb.init_oracle_client(lib_dir=os.path.join(os.path.dirname(__file__), '../dashboard/modules/instantclient_23_7'))
app = Flask(__name__)

def gerar_combo(tamanho=6):

  caracteres = string.ascii_letters + string.digits
  combo = ''.join(random.choices(caracteres, k=tamanho))

  return combo


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
    
    print(f"data: {data}")
    
    if 'hostname' not in data or 'usuario' not in data or 'codigo' not in data:
        salvar_logs_sitema(f"Dados obrigatórios ausentes (hostname, usuario, codigo) por {request_ip} - {id_evento}")
        return jsonify({"error": "Dados obrigatórios ausentes (hostname, usuario, codigo)"}), 400
    
    hostname = data['hostname']
    print(f"hostname: {hostname}")
    usuario = data['usuario']
    print(f"usuario: {usuario}")
    codigo = data['codigo']
    print(f"codigo: {codigo}")
    
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
    
    lista_receptores =  localizar_receptores()
    print(f"Lista de receptores: {lista_receptores}")
    
    if not lista_receptores:
        
        
        salvar_logs_sitema(f"Nenhum receptor encontrado")
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
        print(f"Enviando para receptor: {ip_receptor}")
        
        response = requests.post(
            f"http://{ip_receptor}:9090/alerta5656/enviar",  
            json={"sala": nome_sala, "usuario": nome_usuario, "codigo": "alerta5656"},
            timeout=4
        )
        
        print(f"Resposta do receptor {ip_receptor}: {response.status_code}")
        
        if response.status_code == 200:
            status = "Enviado"
            print(f"[OK] Alerta enviado com sucesso para o receptor {ip_receptor}")
            salvar_logs_sitema(f"Alerta enviado com sucesso para o receptor {ip_receptor}")
        else:
            status = "Erro_HTTP"
            print(f"[ERRO] Erro ao enviar alerta para o receptor {ip_receptor} - Status: {response.status_code}")
            salvar_logs_sitema(f"Erro ao enviar alerta para o receptor {ip_receptor} - Status: {response.status_code}")
            
    except requests.exceptions.ConnectTimeout:
        status = "Timeout"
        print(f"[TIMEOUT] Timeout ao enviar para receptor {ip_receptor}")
        salvar_logs_sitema(f"Timeout ao enviar para receptor {ip_receptor}")
        
    except requests.exceptions.ConnectionError as e:
        status = "Erro_Conexao"
        print(f"[ERRO] Erro de conexão com receptor {ip_receptor}")
        salvar_logs_sitema(f"Erro de conexão com receptor {ip_receptor}: {str(e)}")
        
    except requests.exceptions.RequestException as e:
        status = "Erro_Request"
        print(f"[ERRO] Erro de requisição para receptor {ip_receptor}")
        salvar_logs_sitema(f"Erro de requisição para receptor {ip_receptor}: {str(e)}")
        
    except Exception as e:
        status = "Erro_Geral"
        print(f"[ERRO] Erro inesperado ao enviar para receptor {ip_receptor}")
        salvar_logs_sitema(f"Erro inesperado ao enviar para receptor {ip_receptor}: {str(e)}")
    
    salvar_log_alertas(ip_receptor, hostname_chamador, nome_usuario, nome_sala, data_hora, status, id_evento)



def conectar_banco_de_dados():
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

def obter_proximo_id(sequence_name):
    """Obtém o próximo ID de uma sequence Oracle"""
    conn = conectar_banco_de_dados()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {database_schema}.{sequence_name}.NEXTVAL FROM DUAL")
        proximo_id = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return proximo_id
    except Exception as e:
        print(f"Erro ao obter próximo ID da sequence {sequence_name}: {e}")
        if conn:
            conn.close()
        return None

def salvar_log_alertas(ip_receptor, hostname_chamador, nome_usuario, nome_sala, data_hora, status, id_evento):
    try:
        novo_id = obter_proximo_id(f'seq_botao_log_alerta')
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
            print(f"[OK] Log de alerta salvo com ID: {novo_id}")
    except Exception as e:
        print(f"[ERRO] Falha ao salvar log de alerta: {str(e)}")


def localizar_usuario(usuario):
    conn = conectar_banco_de_dados()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT nome_usuario FROM {database_schema}.da_tbl_botao_usuario WHERE username = :usuario", {'usuario': usuario})
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if result:
                print('###'*10 , result , '###'*10)
                return result[0]
            else:
                print(f"[AVISO] Usuário não encontrado: {usuario}")
                print(f"SELECT nome_usuario FROM {database_schema}.da_tbl_botao_usuario WHERE username = :usuario")
                return None
        except Exception as e:
            print(f"[ERRO] Falha ao localizar usuário {usuario}: {str(e)}")
            if conn:
                conn.close()
            return None
    else:
        return None

def localizar_sala(hostname):
    conn = conectar_banco_de_dados()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT nome_sala FROM {database_schema}.da_tbl_botao_sala WHERE hostname = :hostname", {'hostname': hostname})
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if result:
                return result[0]
            else:
                print(f"[AVISO] Sala não encontrada: {hostname}")
                return "sala Não Encontrada"
        except Exception as e:
            print(f"[ERRO] Falha ao localizar sala {hostname}: {str(e)}")
            if conn:
                conn.close()
            return "sala Não Encontrada"
    else:
        return print("Erro ao conectar ao banco de dados --- localizar sala")

def localizar_receptores():
    conn = conectar_banco_de_dados()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT ip_receptor FROM {database_schema}.da_tbl_botao_receptor")
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            print(f"[INFO] Encontrados {len(result)} receptores no banco")
            return result
        except Exception as e:
            print(f"[ERRO] Falha ao localizar receptores: {str(e)}")
            if conn:
                conn.close()
            return []
    else:
        return []

def salvar_logs_sitema(log):
    try:
        novo_id = obter_proximo_id(f'seq_botao_log_sistema')
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
    app.run(host='0.0.0.0', port=9600)