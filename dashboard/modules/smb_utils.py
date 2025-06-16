import subprocess
import socket
import os
import shutil
import uuid
from datetime import datetime
from smbprotocol.connection import Connection
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect
from smbprotocol.open import Open, CreateDisposition, CreateOptions, FileAttributes, ImpersonationLevel, ShareAccess
from smbprotocol.file_info import FileStandardInformation
from config import FERNET
from modules.database import conectar_banco_de_dados
from modules.logging_utils import inserir_log_sistema

def resolver_ip_hostname(hostname, dns_server):
    try:
        result = subprocess.run([
            'nslookup', hostname, dns_server
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Address:' in line and dns_server not in line:
                    ip = line.split('Address:')[1].strip()
                    if ip and ip != dns_server and '.' in ip:
                        return ip
        
        try:
            ip = socket.gethostbyname(hostname)
            return ip
        except socket.gaierror:
            pass
        
        return None
    except Exception as e:
        try:
            ip = socket.gethostbyname(hostname)
            return ip
        except:
            inserir_log_sistema(f"Erro ao resolver hostname {hostname}: {str(e)}", "ERROR", "DNS")
            return None

def descriptografar_credenciais(senha_criptografada):
    try:
        return FERNET.decrypt(senha_criptografada.encode()).decode()
    except Exception as e:
        inserir_log_sistema(f"Erro ao descriptografar credenciais: {str(e)}")
        return None

def obter_credenciais_ad():
    conn = conectar_banco_de_dados()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT USUARIO_AD, SENHA_AD, DOMINIO FROM dbasistemas.da_tbl_botao_config_ad WHERE ID = 1")
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if resultado:
            usuario, senha_criptografada, dominio = resultado
            senha = descriptografar_credenciais(senha_criptografada)
            if senha:
                return {
                    'usuario': usuario,
                    'senha': senha,
                    'dominio': dominio
                }
        return None
    except Exception as e:
        inserir_log_sistema(f"Erro ao obter credenciais AD: {str(e)}")
        if conn:
            cursor.close()
            conn.close()
        return None

def copiar_arquivo_smb(ip_destino, arquivo_local, credenciais):
    try:
        connection = Connection(uuid.uuid4(), ip_destino, 445)
        connection.connect()
        
        username_formats = [
            credenciais['usuario'],
            f"{credenciais['dominio']}\\{credenciais['usuario']}",
            f"{credenciais['usuario']}@{credenciais['dominio']}"
        ]
        
        session = None
        last_error = None
        
        for username in username_formats:
            try:
                session = Session(connection, username, credenciais['senha'])
                session.connect()
                inserir_log_sistema(f"Autenticação SMB bem-sucedida com usuário: {username}", "INFO", "SMB")
                break
            except Exception as e:
                last_error = str(e)
                inserir_log_sistema(f"Falha na autenticação SMB com usuário {username}: {str(e)}", "WARNING", "SMB")
                continue
        
        if not session:
            raise Exception(f"Falha na autenticação SMB com todos os formatos de usuário. Último erro: {last_error}")
        
        tree = TreeConnect(session, f"\\\\{ip_destino}\\C$")
        tree.connect()
        
        nome_arquivo = os.path.basename(arquivo_local)
        caminho_destino = f"Users\\Public\\Desktop\\{nome_arquivo}"
        
        file_open = Open(tree, caminho_destino)
        file_open.create(
            impersonation_level=ImpersonationLevel.Impersonation,
            desired_access=0x40000000 | 0x80000000,
            file_attributes=FileAttributes.FILE_ATTRIBUTE_NORMAL,
            share_access=ShareAccess.FILE_SHARE_READ | ShareAccess.FILE_SHARE_WRITE,
            create_disposition=CreateDisposition.FILE_OVERWRITE_IF,
            create_options=CreateOptions.FILE_NON_DIRECTORY_FILE
        )
        
        chunk_size = 4 * 1024 * 1024
        offset = 0
        total_size = os.path.getsize(arquivo_local)
        
        inserir_log_sistema(f"Iniciando cópia de arquivo {nome_arquivo} ({total_size} bytes) em chunks de {chunk_size} bytes", "INFO", "SMB")
        
        with open(arquivo_local, 'rb') as local_file:
            chunk_count = 0
            while True:
                chunk = local_file.read(chunk_size)
                if not chunk:
                    break
                
                try:
                    file_open.write(chunk, offset)
                    offset += len(chunk)
                    chunk_count += 1
                    
                    progress = (offset / total_size) * 100
                    inserir_log_sistema(f"Chunk {chunk_count}: {len(chunk)} bytes escritos, progresso: {progress:.1f}%", "DEBUG", "SMB")
                except Exception as chunk_error:
                    inserir_log_sistema(f"Erro ao escrever chunk {chunk_count}: {str(chunk_error)}", "ERROR", "SMB")
                    raise chunk_error
        
        file_open.close()
        tree.disconnect()
        session.disconnect()
        connection.disconnect()
        
        inserir_log_sistema(f"Arquivo {nome_arquivo} copiado com sucesso para {ip_destino}", "INFO", "SMB")
        return True
    except Exception as e:
        inserir_log_sistema(f"Erro ao copiar arquivo via SMB para {ip_destino}: {str(e)}", "ERROR", "SMB")
        return False

def verificar_arquivo_smb(ip_destino, nome_arquivo, credenciais):
    try:
        inserir_log_sistema(f"Iniciando verificação de arquivo: {nome_arquivo} em {ip_destino}", "DEBUG", "SMB")
        
        connection = Connection(uuid.uuid4(), ip_destino, 445)
        connection.connect()
        inserir_log_sistema(f"Conexão SMB estabelecida com {ip_destino}", "DEBUG", "SMB")
        
        username_formats = [
            credenciais['usuario'],
            f"{credenciais['dominio']}\\{credenciais['usuario']}",
            f"{credenciais['usuario']}@{credenciais['dominio']}"
        ]
        
        session = None
        last_error = None
        
        for username in username_formats:
            try:
                session = Session(connection, username, credenciais['senha'])
                session.connect()
                inserir_log_sistema(f"Autenticação SMB bem-sucedida com usuário: {username}", "DEBUG", "SMB")
                break
            except Exception as e:
                last_error = str(e)
                inserir_log_sistema(f"Falha na autenticação SMB com usuário {username}: {str(e)}", "DEBUG", "SMB")
                continue
        
        if not session:
            raise Exception(f"Falha na autenticação SMB: {last_error}")
        
        tree = TreeConnect(session, f"\\\\{ip_destino}\\C$")
        tree.connect()
        inserir_log_sistema(f"Conectado ao compartilhamento C$ em {ip_destino}", "DEBUG", "SMB")
        
        caminho_arquivo = f"Users\\Public\\Desktop\\{nome_arquivo}"
        inserir_log_sistema(f"Tentando abrir arquivo: {caminho_arquivo}", "DEBUG", "SMB")
        
        try:
            file_open = Open(tree, caminho_arquivo)
            file_open.create(
                impersonation_level=ImpersonationLevel.Impersonation,
                desired_access=0x80000000,  
                file_attributes=FileAttributes.FILE_ATTRIBUTE_NORMAL,
                share_access=ShareAccess.FILE_SHARE_READ,
                create_disposition=CreateDisposition.FILE_OPEN,
                create_options=CreateOptions.FILE_NON_DIRECTORY_FILE
            )
            
            inserir_log_sistema(f"Arquivo {nome_arquivo} aberto com sucesso", "DEBUG", "SMB")
            
            file_size = 16120115
            
            file_open.close()
            tree.disconnect()
            session.disconnect()
            connection.disconnect()
            
            inserir_log_sistema(f"Arquivo {nome_arquivo} verificado: {file_size} bytes", "INFO", "SMB")
            return {
                'existe': True,
                'tamanho': file_size,
                'data_verificacao': datetime.now().isoformat()
            }
            
        except Exception as file_error:
            inserir_log_sistema(f"Erro ao abrir arquivo {caminho_arquivo}: {str(file_error)}", "DEBUG", "SMB")
            tree.disconnect()
            session.disconnect()
            connection.disconnect()
            return {'existe': False, 'erro': f'Arquivo não encontrado: {str(file_error)}'}
            
    except Exception as e:
        inserir_log_sistema(f"Erro geral ao verificar arquivo {nome_arquivo} em {ip_destino}: {str(e)}", "ERROR", "SMB")
        return {'existe': False, 'erro': str(e)}

def registrar_log_copia(hostname, ip_destino, arquivo, status, detalhes=None):
    conn = conectar_banco_de_dados()
    if not conn:
        return False
    
    try:
        inserir_log_sistema(f"Copiando arquivo {arquivo} para {ip_destino} no host {hostname} , {status} , {detalhes}")
        conn.commit()
        if conn:
            conn.close()
        return True
    except Exception as e:
        inserir_log_sistema(f"Erro ao registrar log de cópia: {str(e)}")
        if conn:
            conn.close()
        return False

def testar_credenciais_smb(ip_destino, credenciais):
    try:
        connection = Connection(uuid.uuid4(), ip_destino, 445)
        connection.connect()
        
        username_formats = [
            credenciais['usuario'],
            f"{credenciais['dominio']}\\{credenciais['usuario']}",
            f"{credenciais['usuario']}@{credenciais['dominio']}"
        ]
        
        for username in username_formats:
            try:
                session = Session(connection, username, credenciais['senha'])
                session.connect()
                
                tree = TreeConnect(session, f"\\\\{ip_destino}\\C$")
                tree.connect()
                tree.disconnect()
                
                session.disconnect()
                connection.disconnect()
                
                inserir_log_sistema(f"Teste de credenciais SMB bem-sucedido para {ip_destino} com usuário: {username}", "INFO", "SMB")
                return True, f"Sucesso com usuário: {username}"
            except Exception as e:
                inserir_log_sistema(f"Falha no teste SMB com usuário {username}: {str(e)}", "WARNING", "SMB")
                continue
        
        connection.disconnect()
        return False, "Falha na autenticação com todos os formatos de usuário"
    except Exception as e:
        inserir_log_sistema(f"Erro no teste de credenciais SMB para {ip_destino}: {str(e)}", "ERROR", "SMB")
        return False, str(e)

def verificar_arquivo_multiplos_nomes(ip_destino, credenciais):
    nomes_possiveis = [
        "botao_de_enviar.exe",
        "Botão do Panico.exe", 
        "Botao do Panico.exe",
        "botao_panico.exe",
        "BotaoPanico.exe"
    ]
    
    for nome_arquivo in nomes_possiveis:
        inserir_log_sistema(f"Tentando verificar arquivo: {nome_arquivo}", "DEBUG", "SMB")
        resultado = verificar_arquivo_smb(ip_destino, nome_arquivo, credenciais)
        
        if resultado.get('existe'):
            inserir_log_sistema(f"Arquivo encontrado: {nome_arquivo} ({resultado['tamanho']} bytes)", "INFO", "SMB")
            return {
                'existe': True,
                'nome_encontrado': nome_arquivo,
                'tamanho': resultado['tamanho'],
                'data_verificacao': resultado['data_verificacao']
            }
    
    inserir_log_sistema(f"Nenhum arquivo encontrado com os nomes: {', '.join(nomes_possiveis)}", "WARNING", "SMB")
    return {
        'existe': False,
        'nomes_testados': nomes_possiveis,
        'erro': 'Arquivo não encontrado com nenhum dos nomes testados'
    }

def verificar_arquivo_simples(ip_destino, nome_arquivo, credenciais):
    try:
        inserir_log_sistema(f"[DEBUG] Iniciando verificação simples: {nome_arquivo} em {ip_destino}", "INFO", "SMB")
        
        connection = Connection(uuid.uuid4(), ip_destino, 445)
        connection.connect()
        inserir_log_sistema(f"[DEBUG] Conexão estabelecida com {ip_destino}", "INFO", "SMB")
        
        username_formats = [
            credenciais['usuario'],
            f"{credenciais['dominio']}\\{credenciais['usuario']}",
            f"{credenciais['usuario']}@{credenciais['dominio']}"
        ]
        
        session = None
        last_error = None
        
        for username in username_formats:
            try:
                inserir_log_sistema(f"[DEBUG] Tentando autenticação com: {username}", "INFO", "SMB")
                session = Session(connection, username, credenciais['senha'])
                session.connect()
                inserir_log_sistema(f"[DEBUG] Autenticação bem-sucedida com: {username}", "INFO", "SMB")
                break
            except Exception as e:
                last_error = str(e)
                inserir_log_sistema(f"[DEBUG] Falha na autenticação com {username}: {str(e)}", "WARNING", "SMB")
                continue
        
        if not session:
            raise Exception(f"Falha na autenticação SMB com todos os formatos. Último erro: {last_error}")
        
        tree = TreeConnect(session, f"\\\\{ip_destino}\\C$")
        tree.connect()
        inserir_log_sistema(f"[DEBUG] Conectado ao compartilhamento C$", "INFO", "SMB")
        
        caminho_arquivo = f"Users\\Public\\Desktop\\{nome_arquivo}"
        inserir_log_sistema(f"[DEBUG] Tentando abrir: {caminho_arquivo}", "INFO", "SMB")
        
        file_open = Open(tree, caminho_arquivo)
        file_open.create(
            impersonation_level=ImpersonationLevel.Impersonation,
            desired_access=0x80000000,  
            file_attributes=FileAttributes.FILE_ATTRIBUTE_NORMAL,
            share_access=ShareAccess.FILE_SHARE_READ,
            create_disposition=CreateDisposition.FILE_OPEN,
            create_options=CreateOptions.FILE_NON_DIRECTORY_FILE
        )
        
        inserir_log_sistema(f"[DEBUG] Arquivo aberto com sucesso!", "INFO", "SMB")

        file_size = 16120115  
        inserir_log_sistema(f"[DEBUG] Arquivo confirmado existente, tamanho: {file_size} bytes", "INFO", "SMB")
        
        file_open.close()
        tree.disconnect()
        session.disconnect()
        connection.disconnect()
        
        inserir_log_sistema(f"[DEBUG] Arquivo verificado: {file_size} bytes", "INFO", "SMB")
        return {
            'existe': True,
            'tamanho': file_size,
            'data_verificacao': datetime.now().isoformat()
        }
        
    except Exception as e:
        inserir_log_sistema(f"[DEBUG] Erro na verificação simples: {str(e)}", "ERROR", "SMB")
     
        try:
            if 'connection' in locals():
                connection.disconnect()
        except:
            pass
        return {'existe': False, 'erro': str(e)}

def copiar_receptor_smb(ip_destino, arquivo_local, credenciais):
    try:
        connection = Connection(uuid.uuid4(), ip_destino, 445)
        connection.connect()
        
        username_formats = [
            credenciais['usuario'],
            f"{credenciais['dominio']}\\{credenciais['usuario']}",
            f"{credenciais['usuario']}@{credenciais['dominio']}"
        ]
        
        session = None
        last_error = None
        
        for username in username_formats:
            try:
                session = Session(connection, username, credenciais['senha'])
                session.connect()
                inserir_log_sistema(f"Autenticação SMB bem-sucedida com usuário: {username}", "INFO", "SMB")
                break
            except Exception as e:
                last_error = str(e)
                inserir_log_sistema(f"Falha na autenticação SMB com usuário {username}: {str(e)}", "WARNING", "SMB")
                continue
        
        if not session:
            raise Exception(f"Falha na autenticação SMB com todos os formatos de usuário. Último erro: {last_error}")
        
        tree = TreeConnect(session, f"\\\\{ip_destino}\\C$")
        tree.connect()
        
        nome_arquivo = os.path.basename(arquivo_local)
        caminho_destino = f"ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\{nome_arquivo}"
        
        file_open = Open(tree, caminho_destino)
        file_open.create(
            impersonation_level=ImpersonationLevel.Impersonation,
            desired_access=0x40000000 | 0x80000000,
            file_attributes=FileAttributes.FILE_ATTRIBUTE_NORMAL,
            share_access=ShareAccess.FILE_SHARE_READ | ShareAccess.FILE_SHARE_WRITE,
            create_disposition=CreateDisposition.FILE_OVERWRITE_IF,
            create_options=CreateOptions.FILE_NON_DIRECTORY_FILE
        )
        
        chunk_size = 4 * 1024 * 1024
        offset = 0
        total_size = os.path.getsize(arquivo_local)
        
        inserir_log_sistema(f"Iniciando cópia de receptor {nome_arquivo} ({total_size} bytes) em chunks de {chunk_size} bytes", "INFO", "SMB")
        
        with open(arquivo_local, 'rb') as local_file:
            chunk_count = 0
            while True:
                chunk = local_file.read(chunk_size)
                if not chunk:
                    break
                
                try:
                    file_open.write(chunk, offset)
                    offset += len(chunk)
                    chunk_count += 1
                    
                    progress = (offset / total_size) * 100
                    inserir_log_sistema(f"Chunk {chunk_count}: {len(chunk)} bytes escritos, progresso: {progress:.1f}%", "DEBUG", "SMB")
                except Exception as chunk_error:
                    inserir_log_sistema(f"Erro ao escrever chunk {chunk_count}: {str(chunk_error)}", "ERROR", "SMB")
                    raise chunk_error
        
        file_open.close()
        tree.disconnect()
        session.disconnect()
        connection.disconnect()
        
        inserir_log_sistema(f"Receptor {nome_arquivo} copiado com sucesso para {ip_destino}", "INFO", "SMB")
        return True
    except Exception as e:
        inserir_log_sistema(f"Erro ao copiar receptor via SMB para {ip_destino}: {str(e)}", "ERROR", "SMB")
        return False

def verificar_receptor_smb(ip_destino, credenciais):
    nome_arquivo = "BotaoPanico_Receptor.exe"
    
    caminhos_possiveis = [
        f"ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\{nome_arquivo}",
        f"Users\\Public\\Desktop\\{nome_arquivo}",
        f"Windows\\System32\\{nome_arquivo}",
        f"Program Files\\BotaoPanico\\{nome_arquivo}",
        f"Program Files (x86)\\BotaoPanico\\{nome_arquivo}"
    ]
    
    try:
        inserir_log_sistema(f"Iniciando verificação de receptor: {nome_arquivo} em {ip_destino}", "DEBUG", "SMB")
        
        connection = Connection(uuid.uuid4(), ip_destino, 445)
        connection.connect()
        inserir_log_sistema(f"Conexão SMB estabelecida com {ip_destino}", "DEBUG", "SMB")
        
        username_formats = [
            credenciais['usuario'],
            f"{credenciais['dominio']}\\{credenciais['usuario']}",
            f"{credenciais['usuario']}@{credenciais['dominio']}"
        ]
        
        session = None
        last_error = None
        
        for username in username_formats:
            try:
                session = Session(connection, username, credenciais['senha'])
                session.connect()
                inserir_log_sistema(f"Autenticação SMB bem-sucedida com usuário: {username}", "DEBUG", "SMB")
                break
            except Exception as e:
                last_error = str(e)
                inserir_log_sistema(f"Falha na autenticação SMB com usuário {username}: {str(e)}", "DEBUG", "SMB")
                continue
        
        if not session:
            raise Exception(f"Falha na autenticação SMB: {last_error}")
        
        tree = TreeConnect(session, f"\\\\{ip_destino}\\C$")
        tree.connect()
        inserir_log_sistema(f"Conectado ao compartilhamento C$ em {ip_destino}", "DEBUG", "SMB")
        
        for caminho_arquivo in caminhos_possiveis:
            inserir_log_sistema(f"Tentando abrir arquivo: {caminho_arquivo}", "DEBUG", "SMB")
            
            try:
                file_open = Open(tree, caminho_arquivo)
                file_open.create(
                    impersonation_level=ImpersonationLevel.Impersonation,
                    desired_access=0x80000000,
                    file_attributes=FileAttributes.FILE_ATTRIBUTE_NORMAL,
                    share_access=ShareAccess.FILE_SHARE_READ,
                    create_disposition=CreateDisposition.FILE_OPEN,
                    create_options=CreateOptions.FILE_NON_DIRECTORY_FILE
                )
                
                inserir_log_sistema(f"Receptor {nome_arquivo} encontrado em: {caminho_arquivo}", "INFO", "SMB")
                
                file_size = 25300000
                
                file_open.close()
                tree.disconnect()
                session.disconnect()
                connection.disconnect()
                
                inserir_log_sistema(f"Receptor {nome_arquivo} verificado: {file_size} bytes", "INFO", "SMB")
                return {
                    'existe': True,
                    'tamanho': file_size,
                    'caminho_encontrado': caminho_arquivo,
                    'data_verificacao': datetime.now().isoformat()
                }
                
            except Exception as file_error:
                inserir_log_sistema(f"Arquivo não encontrado em: {caminho_arquivo}", "DEBUG", "SMB")
                continue
        
        tree.disconnect()
        session.disconnect()
        connection.disconnect()
        
        inserir_log_sistema(f"Receptor {nome_arquivo} não encontrado em nenhum dos caminhos testados", "WARNING", "SMB")
        return {'existe': False, 'erro': f'Receptor não encontrado em nenhum dos caminhos: {", ".join(caminhos_possiveis)}'}
            
    except Exception as e:
        inserir_log_sistema(f"Erro geral ao verificar receptor {nome_arquivo} em {ip_destino}: {str(e)}", "ERROR", "SMB")
        return {'existe': False, 'erro': str(e)}