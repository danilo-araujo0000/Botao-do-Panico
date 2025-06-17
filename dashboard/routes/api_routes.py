from flask import Blueprint, request, jsonify
from datetime import datetime
from modules.auth import login_required, criptografar_senha, criptografar_reversivel
from modules.database import conectar_banco_de_dados, obter_proximo_id, DATABASE_SCHEMA
from modules.logging_utils import inserir_log_sistema
from modules.ad_integration import consultar_hostnames_ad, consultar_usuarios_ad
from modules.smb_utils import *
import os
import dotenv
import requests
from requests.exceptions import RequestException, ConnectTimeout, ConnectionError
dotenv.load_dotenv()

path_exe_botao  = os.getenv('PATH_EXE_BOTAO')
dns_server = os.getenv('DNS_SERVER')
path_receptor =r"C:\py\BASE\botao\dist\BotaoPanico_Receptor.exe"

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/salas', methods=['POST'])
@login_required
def adicionar_sala():
    data_agora = datetime.now()
    data = request.get_json()
    novo_id = obter_proximo_id(f'seq_botao_sala')
    if not novo_id:
        return jsonify({'error': 'Erro ao obter ID da sequence'}), 500
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            INSERT INTO {DATABASE_SCHEMA}.da_tbl_botao_sala
            (id, nome_sala, hostname, setor, data_criacao, data_atualizacao, status_instalacao)
            VALUES (:id, :nome_sala, :hostname, :setor, :data_criacao, :data_atualizacao, :status_instalacao)
        """, {
            'id': novo_id,
            'nome_sala': data['nome_sala'], 
            'hostname': data['hostname'], 
            'setor': data.get('setor', ''),
            'data_criacao': data_agora,
            'data_atualizacao': data_agora,
            'status_instalacao': 'Não verificado'
        })
        conn.commit()
        inserir_log_sistema(f'Nova sala adicionada: {data["nome_sala"]} (ID: {novo_id})', 'INFO', 'CRUD_SALA')
        return jsonify({'success': True, 'id': novo_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/salas/<int:sala_id>', methods=['PUT'])
@login_required
def editar_sala(sala_id):
    data = request.get_json()
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            UPDATE {DATABASE_SCHEMA}.da_tbl_botao_sala 
            SET nome_sala = :nome_sala, hostname = :hostname, setor = :setor, data_atualizacao = :data_atualizacao
            WHERE id = :id
        """, {
            'nome_sala': data['nome_sala'], 
            'hostname': data['hostname'], 
            'setor': data.get('setor', ''), 
            'data_atualizacao': datetime.now(),
            'id': sala_id
        })
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/salas/<int:sala_id>', methods=['DELETE'])
@login_required
def deletar_sala(sala_id):
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {DATABASE_SCHEMA}.da_tbl_botao_sala WHERE id = :id", {'id': sala_id})
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/salas/<int:sala_id>/status', methods=['PUT'])
@login_required
def atualizar_status_sala(sala_id):
    data = request.get_json()
    status = data.get('status_instalacao')
    
    if not status:
        return jsonify({'error': 'Status é obrigatório'}), 400
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            UPDATE {DATABASE_SCHEMA}.da_tbl_botao_sala 
            SET status_instalacao = :status 
            WHERE id = :id
        """, {
            'status': status,
            'id': sala_id
        })
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/usuarios', methods=['POST'])
@login_required
def adicionar_usuario():
    data = request.get_json()
    
    novo_id = obter_proximo_id(f'seq_botao_usuario')
    if not novo_id:
        return jsonify({'error': 'Erro ao obter ID da sequence'}), 500
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    use_minusculo = data['USERNAME'].upper()
    try:
        cursor.execute(f"""
            INSERT INTO {DATABASE_SCHEMA}.da_tbl_botao_usuario (id, nome_usuario, username) 
            VALUES (:id, :nome_usuario, :username)
        """, {
            'id': novo_id,
            'nome_usuario': data['nome_usuario'], 
            'username': use_minusculo
        })
        conn.commit()
        return jsonify({'success': True, 'id': novo_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/usuarios/<int:usuario_id>', methods=['PUT'])
@login_required
def editar_usuario(usuario_id):
    data = request.get_json()
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    use_minusculo = data['USERNAME'].upper()
    try:
        cursor.execute(f"""
            UPDATE {DATABASE_SCHEMA}.da_tbl_botao_usuario 
            SET nome_usuario = :nome_usuario, username = :username 
            WHERE id = :id
        """, {
            'nome_usuario': data['nome_usuario'], 
            'username': use_minusculo, 
            'id': usuario_id
        })
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/usuarios/<int:usuario_id>', methods=['DELETE'])
@login_required
def deletar_usuario(usuario_id):
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {DATABASE_SCHEMA}.da_tbl_botao_usuario WHERE id = :id", {'id': usuario_id})
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/receptores', methods=['POST'])
@login_required
def adicionar_receptor():
    data = request.get_json()
    
    novo_id = obter_proximo_id(f'seq_botao_receptor')
    if not novo_id:
        return jsonify({'error': 'Erro ao obter ID da sequence'}), 500
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            INSERT INTO {DATABASE_SCHEMA}.da_tbl_botao_receptor (id, ip_receptor, nome_receptor, setor) 
            VALUES (:id, :ip_receptor, :nome_receptor, :setor)
        """, {
            'id': novo_id,
            'ip_receptor': data['ip_receptor'], 
            'nome_receptor': data.get('nome_receptor', ''), 
            'setor': data.get('setor', '')
        })
        conn.commit()
        return jsonify({'success': True, 'id': novo_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/receptores/<int:receptor_id>', methods=['PUT'])
@login_required
def editar_receptor(receptor_id):
    data = request.get_json()
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            UPDATE {DATABASE_SCHEMA}.da_tbl_botao_receptor 
            SET ip_receptor = :ip_receptor, nome_receptor = :nome_receptor, setor = :setor 
            WHERE id = :id
        """, {
            'ip_receptor': data['ip_receptor'], 
            'nome_receptor': data.get('nome_receptor', ''), 
            'setor': data.get('setor', ''), 
            'id': receptor_id
        })
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/receptores/<int:receptor_id>', methods=['DELETE'])
@login_required
def deletar_receptor(receptor_id):
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {DATABASE_SCHEMA}.da_tbl_botao_receptor WHERE id = :id", {'id': receptor_id})
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/usuarios-login', methods=['POST'])
@login_required
def adicionar_usuario_login():
    data = request.get_json()
    
    novo_id = obter_proximo_id(f'seq_botao_usuario_login')
    if not novo_id:
        return jsonify({'error': 'Erro ao obter ID da sequence'}), 500
    
    senha_hash = criptografar_senha(data['senha'])
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            INSERT INTO {DATABASE_SCHEMA}.da_tbl_botao_usuario_login (id, usuario, senha) 
            VALUES (:id, :usuario, :senha)
        """, {
            'id': novo_id,
            'usuario': data['usuario'], 
            'senha': senha_hash
        })
        conn.commit()
        
        inserir_log_sistema(f'Usuário de login criado: {data["usuario"]}', 'INFO', 'CONFIG')
        
        return jsonify({'success': True, 'id': novo_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/usuarios-login/<int:usuario_id>', methods=['PUT'])
@login_required
def editar_usuario_login(usuario_id):
    data = request.get_json()
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        if 'senha' in data and data['senha']:
            senha_hash = criptografar_senha(data['senha'])
            cursor.execute(f"""
                UPDATE {DATABASE_SCHEMA}.da_tbl_botao_usuario_login 
                SET usuario = :usuario, senha = :senha 
                WHERE id = :id
            """, {
                'usuario': data['usuario'], 
                'senha': senha_hash, 
                'id': usuario_id
            })
        else:
            cursor.execute(f"""
                UPDATE {DATABASE_SCHEMA}.da_tbl_botao_usuario_login 
                SET usuario = :usuario 
                WHERE id = :id
            """, {
                'usuario': data['usuario'], 
                'id': usuario_id
            })
        
        conn.commit()
        
        inserir_log_sistema(f'Usuário de login editado: {data["usuario"]}', 'INFO', 'CONFIG')
        
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/usuarios-login/<int:usuario_id>', methods=['DELETE'])
@login_required
def deletar_usuario_login(usuario_id):
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT usuario FROM {DATABASE_SCHEMA}.da_tbl_botao_usuario_login WHERE id = :id", {'id': usuario_id})
        resultado = cursor.fetchone()
        nome_usuario = resultado[0] if resultado else 'Desconhecido'
        
        cursor.execute(f"DELETE FROM {DATABASE_SCHEMA}.da_tbl_botao_usuario_login WHERE id = :id", {'id': usuario_id})
        conn.commit()
        
        inserir_log_sistema(f'Usuário de login deletado: {nome_usuario}', 'WARNING', 'CONFIG')
        
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/config/ad', methods=['POST'])
@login_required
def salvar_config_ad():
    data = request.get_json()
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT id FROM {DATABASE_SCHEMA}.da_tbl_botao_config_ad WHERE id = 1")
        existe = cursor.fetchone()
        
        if existe:
            if 'ad_senha' in data:
                senha_criptografada = criptografar_reversivel(data['ad_senha'])
                cursor.execute(f"""
                    UPDATE {DATABASE_SCHEMA}.da_tbl_botao_config_ad 
                    SET usuario_ad = :usuario, senha_ad = :senha, dominio = :dominio 
                    WHERE id = 1
                """, {
                    'usuario': data['ad_usuario'],
                    'senha': senha_criptografada,
                    'dominio': data['ad_dominio']
                })
            else:
                cursor.execute(f"""
                    UPDATE {DATABASE_SCHEMA}.da_tbl_botao_config_ad 
                    SET usuario_ad = :usuario, dominio = :dominio 
                    WHERE id = 1
                """, {
                    'usuario': data['ad_usuario'],
                    'dominio': data['ad_dominio']
                })
        else:
            if 'ad_senha' not in data:
                return jsonify({'error': 'Senha do AD é obrigatória para configuração inicial'}), 400
                
            senha_criptografada = criptografar_reversivel(data['ad_senha'])
            cursor.execute(f"""
                INSERT INTO {DATABASE_SCHEMA}.da_tbl_botao_config_ad (id, usuario_ad, senha_ad, dominio) 
                VALUES (1, :usuario, :senha, :dominio)
            """, {
                'usuario': data['ad_usuario'],
                'senha': senha_criptografada,
                'dominio': data['ad_dominio']
            })
        
        conn.commit()
        inserir_log_sistema('Configurações do Active Directory atualizadas', 'INFO', 'CONFIG')
        return jsonify({'success': True})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        if conn:
            conn.close()

@api_bp.route('/api/ad/hostnames')
@login_required
def obter_hostnames_ad():
    sucesso, resultado = consultar_hostnames_ad()
    
    if sucesso:
        return jsonify({
            'success': True,
            'hostnames': resultado
        })
    else:
        inserir_log_sistema(f"Erro ao consultar hostnames do AD: {resultado}", "ERROR", "AD")
        return jsonify({
            'success': False,
            'error': f"Falha ao obter hostnames do AD: {resultado}"
        }), 500

@api_bp.route('/api/ad/importar-hostnames', methods=['POST'])
@login_required
def importar_hostnames():
    data = request.get_json()
    hostnames = data.get('hostnames', [])
    
    if not hostnames:
        return jsonify({
            'success': False,
            'error': 'Nenhum hostname fornecido'
        }), 400
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({
            'success': False,
            'error': 'Erro ao conectar ao banco de dados'
        }), 500
    
    try:
        cursor = conn.cursor()
        
        hostnames_existentes = []
        cursor.execute(f"SELECT hostname FROM {DATABASE_SCHEMA}.da_tbl_botao_sala")
        for row in cursor.fetchall():
            hostnames_existentes.append(row[0].lower())
        
        importados = 0
        for hostname in hostnames:
            if hostname.lower() not in hostnames_existentes:
                novo_id = obter_proximo_id(f'seq_botao_sala')
                if not novo_id:
                    continue
                
                cursor.execute(f"""
                    INSERT INTO {DATABASE_SCHEMA}.da_tbl_botao_sala
                    (id, nome_sala, hostname, setor, data_criacao, data_atualizacao)
                    VALUES (:id, :nome_sala, :hostname, :setor, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, {
                    'id': novo_id,
                    'nome_sala': f"Sala {hostname}",
                    'hostname': hostname,
                    'setor': 'Importado do AD'
                })
                importados += 1
        
        conn.commit()
        inserir_log_sistema(f"Importados {importados} hostnames do Active Directory", "INFO", "AD")
        
        return jsonify({
            'success': True,
            'importados': importados
        })
    except Exception as e:
        conn.rollback()
        inserir_log_sistema(f"Erro ao importar hostnames: {str(e)}", "ERROR", "AD")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@api_bp.route('/api/copiar-arquivo', methods=['POST'])
@login_required
def copiar_arquivo():
    data = request.get_json()
    hostname = data.get('hostname')
    
    if not hostname:
        return jsonify({
            'success': False,
            'error': 'Hostname é obrigatório'
        }), 400
    
    ip_destino = resolver_ip_hostname(hostname, dns_server)
    if not ip_destino:
        registrar_log_copia(hostname, None, path_exe_botao, 'ERRO', 'Falha na resolução DNS')
        return jsonify({
            'success': False,
            'error': f'Não foi possível resolver o IP do hostname {hostname}'
        }), 400
    
    credenciais = obter_credenciais_ad()
    if not credenciais:
        registrar_log_copia(hostname, ip_destino, path_exe_botao, 'ERRO', 'Credenciais AD não encontradas')
        return jsonify({
            'success': False,
            'error': 'Credenciais do Active Directory não configuradas'
        }), 400
    
    sucesso = copiar_arquivo_smb(ip_destino, path_exe_botao, credenciais)
    
    if sucesso:
        registrar_log_copia(hostname, ip_destino, path_exe_botao, 'SUCESSO', 'Arquivo copiado com sucesso')
        inserir_log_sistema(f"Arquivo copiado para {hostname} ({ip_destino})", "INFO", "SMB_COPY")
        return jsonify({
            'success': True,
            'message': f'Arquivo copiado com sucesso para {hostname} ({ip_destino})'
        })
    else:
        registrar_log_copia(hostname, ip_destino, path_exe_botao, 'ERRO', 'Falha na cópia SMB')
        return jsonify({
            'success': False,
            'error': f'Falha ao copiar arquivo para {hostname} ({ip_destino})'
        }), 500

@api_bp.route('/api/verificar-arquivo', methods=['POST'])
@login_required
def verificar_arquivo():
    data = request.get_json()
    hostname = data.get('hostname')
    
    if not hostname:
        return jsonify({
            'success': False,
            'error': 'Hostname é obrigatório'
        }), 400
    
    ip_destino = resolver_ip_hostname(hostname, dns_server)
    if not ip_destino:
        return jsonify({
            'success': False,
            'error': f'Não foi possível resolver o IP do hostname {hostname}'
        }), 400
    
    credenciais = obter_credenciais_ad()
    if not credenciais:
        return jsonify({
            'success': False,
            'error': 'Credenciais do Active Directory não configuradas'
        }), 400
    
    resultado = verificar_arquivo_multiplos_nomes(ip_destino, credenciais)
    
    if resultado.get('existe'):
        nome_encontrado = resultado.get('nome_encontrado', 'arquivo')
        inserir_log_sistema(f"Arquivo verificado em {hostname} ({ip_destino}) - {nome_encontrado}: {resultado['tamanho']} bytes", "INFO", "SMB_CHECK")
        return jsonify({
            'success': True,
            'existe': True,
            'nome_arquivo': nome_encontrado,
            'tamanho': resultado['tamanho'],
            'data_verificacao': resultado['data_verificacao'],
            'hostname': hostname,
            'ip': ip_destino
        })
    else:
        nomes_testados = resultado.get('nomes_testados', [])
        inserir_log_sistema(f"Arquivo não encontrado em {hostname} ({ip_destino}) - Testados: {', '.join(nomes_testados)}", "WARNING", "SMB_CHECK")
        return jsonify({
            'success': True,
            'existe': False,
            'erro': resultado.get('erro', 'Arquivo não encontrado'),
            'nomes_testados': nomes_testados,
            'hostname': hostname,
            'ip': ip_destino
        }) 

@api_bp.route('/api/ad/usuarios')
@login_required
def obter_usuarios_ad():
    sucesso, resultado = consultar_usuarios_ad()
    
    if sucesso:
        conn = conectar_banco_de_dados()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(f"SELECT username FROM {DATABASE_SCHEMA}.da_tbl_botao_usuario")
                usuarios_existentes = [row[0].upper() for row in cursor.fetchall()]
                cursor.close()
                conn.close()
                
                usuarios_filtrados = [
                    usuario for usuario in resultado 
                    if usuario.get('username', '').upper() not in usuarios_existentes
                ]
                
                return jsonify({
                    'success': True,
                    'usuarios': usuarios_filtrados
                })
            except Exception as e:
                if conn:
                    conn.close()
                inserir_log_sistema(f"Erro ao filtrar usuários já importados: {str(e)}", "ERROR", "AD")
        
        return jsonify({
            'success': True,
            'usuarios': resultado
        })
    else:
        inserir_log_sistema(f"Erro ao consultar usuários do AD: {resultado}", "ERROR", "AD")
        return jsonify({
            'success': False,
            'error': f"Falha ao obter usuários do AD: {resultado}"
        }), 500

@api_bp.route('/api/ad/importar-usuarios', methods=['POST'])
@login_required
def importar_usuarios():
    data = request.get_json()
    usuarios = data.get('usuarios', [])
    
    if not usuarios:
        return jsonify({
            'success': False,
            'error': 'Nenhum usuário fornecido'
        }), 400
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({
            'success': False,
            'error': 'Erro ao conectar ao banco de dados'
        }), 500
    
    try:
        cursor = conn.cursor()
        
        usuarios_existentes = []
        cursor.execute(f"SELECT username FROM {DATABASE_SCHEMA}.da_tbl_botao_usuario")
        for row in cursor.fetchall():
            usuarios_existentes.append(row[0].upper())
        
        importados = 0
        for usuario in usuarios:
            username = usuario.get('username', '').upper()
            nome_completo = usuario.get('nome_completo', '')
            
            if username and nome_completo and username not in usuarios_existentes:
                novo_id = obter_proximo_id(f'seq_botao_usuario')
                if not novo_id:
                    continue
                
                cursor.execute(f"""
                    INSERT INTO {DATABASE_SCHEMA}.da_tbl_botao_usuario
                    (id, nome_usuario, username)
                    VALUES (:id, :nome_usuario, :username)
                """, {
                    'id': novo_id,
                    'nome_usuario': nome_completo,
                    'username': username
                })
                importados += 1
        
        conn.commit()
        inserir_log_sistema(f"Importados {importados} usuários do Active Directory", "INFO", "AD")
        
        return jsonify({
            'success': True,
            'importados': importados
        })
    except Exception as e:
        conn.rollback()
        inserir_log_sistema(f"Erro ao importar usuários: {str(e)}", "ERROR", "AD")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@api_bp.route('/api/sincronizacao/usuarios/config', methods=['GET'])
@login_required
def obter_config_sincronizacao():
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({
            'success': False,
            'error': 'Erro ao conectar ao banco de dados'
        }), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT ativa, tipo, hora, dia_semana, dia_mes, ultima_execucao, proxima_execucao
            FROM {DATABASE_SCHEMA}.da_tbl_botao_sinc_user
            WHERE id = 1
        """)
        
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if resultado:
            config = {
                'ativa': bool(resultado[0]),
                'tipo': resultado[1],
                'hora': resultado[2],
                'dia_semana': resultado[3],
                'dia_mes': resultado[4],
                'ultima_execucao': resultado[5].strftime('%d/%m/%Y %H:%M') if resultado[5] else None,
                'proxima_execucao': resultado[6].strftime('%d/%m/%Y %H:%M') if resultado[6] else None
            }
        else:
            config = {
                'ativa': False,
                'tipo': 'diario',
                'hora': '02:00',
                'dia_semana': 0,
                'dia_mes': 1,
                'ultima_execucao': None,
                'proxima_execucao': None
            }
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        if conn:
            conn.close()
        inserir_log_sistema(f"Erro ao obter configuração de sincronização: {str(e)}", "ERROR", "SYNC")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/api/sincronizacao/usuarios/config', methods=['POST'])
@login_required
def salvar_config_sincronizacao():
    data = request.get_json()
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({
            'success': False,
            'error': 'Erro ao conectar ao banco de dados'
        }), 500
    
    try:
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM {DATABASE_SCHEMA}.da_tbl_botao_sinc_user WHERE id = 1
        """)
        existe = cursor.fetchone()[0] > 0
        
        if existe:
            cursor.execute(f"""
                UPDATE {DATABASE_SCHEMA}.da_tbl_botao_sinc_user 
                SET ativa = :ativa, tipo = :tipo, hora = :hora, 
                    dia_semana = :dia_semana, dia_mes = :dia_mes,
                    data_atualizacao = CURRENT_TIMESTAMP
                WHERE id = 1
            """, {
                'ativa': 1 if data.get('ativa') else 0,
                'tipo': data.get('tipo', 'diario'),
                'hora': data.get('hora', '02:00'),
                'dia_semana': data.get('dia_semana', 0),
                'dia_mes': data.get('dia_mes', 1)
            })
        else:
            cursor.execute(f"""
                INSERT INTO {DATABASE_SCHEMA}.da_tbl_botao_sinc_user
                (id, ativa, tipo, hora, dia_semana, dia_mes, data_criacao, data_atualizacao)
                VALUES (1, :ativa, :tipo, :hora, :dia_semana, :dia_mes, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, {
                'ativa': 1 if data.get('ativa') else 0,
                'tipo': data.get('tipo', 'diario'),
                'hora': data.get('hora', '02:00'),
                'dia_semana': data.get('dia_semana', 0),
                'dia_mes': data.get('dia_mes', 1)
            })
        
        conn.commit()
        cursor.close()
        conn.close()
        
        from modules.sync_scheduler import atualizar_agendamento_sincronizacao
        atualizar_agendamento_sincronizacao()
        
        inserir_log_sistema("Configuração de sincronização de usuários atualizada", "INFO", "SYNC")
        
        return jsonify({
            'success': True,
            'message': 'Configuração salva com sucesso'
        })
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        inserir_log_sistema(f"Erro ao salvar configuração de sincronização: {str(e)}", "ERROR", "SYNC")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/api/testar-credenciais', methods=['POST'])
@login_required
def testar_credenciais():
    data = request.get_json()
    hostname = data.get('hostname')
    
    if not hostname:
        return jsonify({
            'success': False,
            'error': 'Hostname é obrigatório'
        }), 400
    
    ip_destino = resolver_ip_hostname(hostname, dns_server)
    if not ip_destino:
        return jsonify({
            'success': False,
            'error': f'Não foi possível resolver o IP do hostname {hostname}'
        }), 400
    
    credenciais = obter_credenciais_ad()
    if not credenciais:
        return jsonify({
            'success': False,
            'error': 'Credenciais do Active Directory não configuradas'
        }), 400
    
    sucesso, mensagem = testar_credenciais_smb(ip_destino, credenciais)
    
    if sucesso:
        return jsonify({
            'success': True,
            'message': f'Credenciais válidas para {hostname} ({ip_destino}): {mensagem}',
            'hostname': hostname,
            'ip': ip_destino
        })
    else:
        return jsonify({
            'success': False,
            'error': f'Falha na autenticação para {hostname} ({ip_destino}): {mensagem}',
            'hostname': hostname,
            'ip': ip_destino
        }), 401 

@api_bp.route('/api/debug/verificar-arquivo', methods=['POST'])
@login_required
def debug_verificar_arquivo():
    data = request.get_json()
    hostname = data.get('hostname')
    
    if not hostname:
        return jsonify({'error': 'Hostname é obrigatório'}), 400
    
    ip_destino = resolver_ip_hostname(hostname, dns_server)
    if not ip_destino:
        return jsonify({'error': f'Não foi possível resolver o IP do hostname {hostname}'}), 400
    
    credenciais = obter_credenciais_ad()
    if not credenciais:
        return jsonify({'error': 'Credenciais do Active Directory não configuradas'}), 400
    

    nomes_possiveis = [
        "botao_de_enviar.exe",
        "Botão do Panico.exe", 
        "Botao do Panico.exe",
        "botao_panico.exe",
        "BotaoPanico.exe"
    ]
    
    resultados = []
    for nome in nomes_possiveis:
        resultado = verificar_arquivo_smb(ip_destino, nome, credenciais)
        resultados.append({
            'nome': nome,
            'existe': resultado.get('existe', False),
            'tamanho': resultado.get('tamanho', 0),
            'erro': resultado.get('erro', '')
        })
    
    return jsonify({
        'hostname': hostname,
        'ip': ip_destino,
        'resultados': resultados
    }) 

@api_bp.route('/api/teste-arquivo-simples', methods=['POST'])
@login_required
def teste_arquivo_simples():
    data = request.get_json()
    hostname = data.get('hostname', 'PainelSTI')
    
    ip_destino = resolver_ip_hostname(hostname, dns_server)
    if not ip_destino:
        return jsonify({'error': f'Não foi possível resolver o IP do hostname {hostname}'}), 400
    
    credenciais = obter_credenciais_ad()
    if not credenciais:
        return jsonify({'error': 'Credenciais do Active Directory não configuradas'}), 400
    

    resultado = verificar_arquivo_smb(ip_destino, "botao_de_enviar.exe", credenciais)
    
    return jsonify({
        'hostname': hostname,
        'ip': ip_destino,
        'arquivo_testado': 'botao_de_enviar.exe',
        'resultado': resultado
    }) 

@api_bp.route('/api/debug/credenciais', methods=['GET'])
@login_required
def debug_credenciais():
    credenciais = obter_credenciais_ad()
    
    if not credenciais:
        return jsonify({'error': 'Credenciais não encontradas'}), 400
    
    return jsonify({
        'usuario': credenciais['usuario'],
        'dominio': credenciais['dominio'],
        'senha_existe': bool(credenciais.get('senha')),
        'formatos_teste': [
            credenciais['usuario'],
            f"{credenciais['dominio']}\\{credenciais['usuario']}",
            f"{credenciais['usuario']}@{credenciais['dominio']}"
        ]
    }) 

@api_bp.route('/api/logs/sistema/limpar', methods=['DELETE'])
@login_required
def limpar_logs_sistema():
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({
            'success': False,
            'error': 'Erro ao conectar ao banco de dados'
        }), 500
    
    try:
        cursor = conn.cursor()
        

        cursor.execute(f"""
            SELECT COUNT(*) FROM {DATABASE_SCHEMA}.da_tbl_botao_log_sistema
        """)
        total_logs = cursor.fetchone()[0]
        

        cursor.execute(f"""
            DELETE FROM {DATABASE_SCHEMA}.da_tbl_botao_log_sistema
        """)
        
        conn.commit()
        

        inserir_log_sistema(f"Limpeza de logs de sistema executada - {total_logs} registros removidos", "INFO", "SISTEMA")
        
        return jsonify({
            'success': True,
            'removidos': total_logs,
            'message': f'{total_logs} logs de sistema removidos com sucesso'
        })
        
    except Exception as e:
        conn.rollback()
        inserir_log_sistema(f"Erro ao limpar logs de sistema: {str(e)}", "ERROR", "SISTEMA")
        return jsonify({
            'success': False,
            'error': f'Erro ao limpar logs de sistema: {str(e)}'
        }), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@api_bp.route('/api/receptor/instalar', methods=['POST'])
@login_required
def instalar_receptor():
    data = request.get_json()
    ip_receptor = data.get('ip_receptor')
    receptor_id = data.get('receptor_id')
    
    if not ip_receptor:
        return jsonify({
            'success': False,
            'error': 'IP ou hostname do receptor é obrigatório'
        }), 400
    
    if not path_receptor:
        return jsonify({
            'success': False,
            'error': 'Caminho do receptor não configurado'
        }), 500
    
    credenciais = obter_credenciais_ad()
    if not credenciais:
        return jsonify({
            'success': False,
            'error': 'Credenciais do Active Directory não configuradas'
        }), 400
    
    try:
        sucesso = copiar_receptor_smb(ip_receptor, path_receptor, credenciais)
        
        if sucesso:
            if receptor_id:
                conn = conectar_banco_de_dados()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute(f"""
                            UPDATE {DATABASE_SCHEMA}.da_tbl_botao_receptor 
                            SET status_receptor = :status 
                            WHERE id = :id
                        """, {
                            'status': 'Instalado',
                            'id': receptor_id
                        })
                        conn.commit()
                    except Exception as e:
                        inserir_log_sistema(f"Erro ao atualizar status do receptor {receptor_id}: {str(e)}", "ERROR", "RECEPTOR")
                    finally:
                        cursor.close()
                        conn.close()
            
            inserir_log_sistema(f"Receptor instalado com sucesso em {ip_receptor}", "INFO", "RECEPTOR")
            return jsonify({
                'success': True,
                'message': f'Receptor instalado com sucesso em {ip_receptor}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Falha ao instalar receptor em {ip_receptor}'
            }), 500
            
    except Exception as e:
        inserir_log_sistema(f"Erro ao instalar receptor em {ip_receptor}: {str(e)}", "ERROR", "RECEPTOR")
        return jsonify({
            'success': False,
            'error': f'Erro ao instalar receptor: {str(e)}'
        }), 500

@api_bp.route('/api/receptor/verificar', methods=['POST'])
@login_required
def verificar_receptor():
    data = request.get_json()
    ip_receptor = data.get('ip_receptor')
    receptor_id = data.get('receptor_id')
    
    if not ip_receptor:
        return jsonify({
            'success': False,
            'error': 'IP ou hostname do receptor é obrigatório'
        }), 400
    
    credenciais = obter_credenciais_ad()
    if not credenciais:
        return jsonify({
            'success': False,
            'error': 'Credenciais do Active Directory não configuradas'
        }), 400
    
    try:
        resultado = verificar_receptor_smb(ip_receptor, credenciais)
        
        if receptor_id:
            conn = conectar_banco_de_dados()
            if conn:
                try:
                    cursor = conn.cursor()
                    status = 'Instalado' if resultado.get('existe') else 'Não instalado'
                    cursor.execute(f"""
                        UPDATE {DATABASE_SCHEMA}.da_tbl_botao_receptor 
                        SET status_receptor = :status 
                        WHERE id = :id
                    """, {
                        'status': status,
                        'id': receptor_id
                    })
                    conn.commit()
                except Exception as e:
                    inserir_log_sistema(f"Erro ao atualizar status do receptor {receptor_id}: {str(e)}", "ERROR", "RECEPTOR")
                finally:
                    cursor.close()
                    conn.close()
        
        return jsonify({
            'existe': resultado.get('existe', False),
            'tamanho': resultado.get('tamanho', 0),
            'ip_receptor': ip_receptor
        })
        
    except Exception as e:
        inserir_log_sistema(f"Erro ao verificar receptor em {ip_receptor}: {str(e)}", "ERROR", "RECEPTOR")
        return jsonify({
            'existe': False,
            'error': str(e)
        }), 500

@api_bp.route('/api/receptor/testar-conexao', methods=['POST'])
@login_required
def testar_conexao_receptor():
    data = request.get_json()
    ip_receptor = data.get('ip_receptor')
    
    if not ip_receptor:
        return jsonify({
            'success': False,
            'error': 'IP ou hostname do receptor é obrigatório'
        }), 400
    
    try:
        response = requests.get(
            f"http://{ip_receptor}:9090/check-health", 
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'status': 'online',
                'message': 'Receptor online'
            })
        else:
            return jsonify({
                'success': True,
                'status': 'error',
                'message': f'Receptor respondeu com status {response.status_code}'
            })
            
    except ConnectTimeout:
        return jsonify({
            'success': True,
            'status': 'timeout',
            'message': 'Timeout na conexão'
        })
    except ConnectionError:
        return jsonify({
            'success': True,
            'status': 'offline',
            'message': 'Receptor offline'
        })
    except RequestException as e:
        return jsonify({
            'success': True,
            'status': 'error',
            'message': f'Erro na requisição: {str(e)}'
        })
    except Exception as e:
        inserir_log_sistema(f"Erro ao testar conectividade do receptor {ip_receptor}: {str(e)}", "ERROR", "RECEPTOR")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500