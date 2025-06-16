from datetime import datetime
from flask import session
from modules.database import conectar_banco_de_dados, obter_proximo_id, DATABASE_SCHEMA

def inserir_log_sistema(mensagem, nivel='INFO', modulo='DASHBOARD', usuario=None):
    novo_id = obter_proximo_id(f'seq_botao_log_sistema')
    if not novo_id:
        print("Erro ao obter ID para log do sistema")
        return False
    
    conn = conectar_banco_de_dados()
    if not conn:
        print("Erro ao conectar com banco para log")
        return False
    
    try:
        cursor = conn.cursor()
        usuario_atual = usuario
        if usuario is None and 'usuario_logado' in session:
            usuario_atual = session.get('usuario_logado', 'SISTEMA')
        else:
            usuario_atual = usuario or 'SISTEMA'
            
        cursor.execute(f"""
            INSERT INTO {DATABASE_SCHEMA}.da_tbl_botao_log_sistema (id, log, nivel, modulo, usuario) 
            VALUES (:id, :log, :nivel, :modulo, :usuario)
        """, {
            'id': novo_id,
            'log': mensagem,
            'nivel': nivel,
            'modulo': modulo,
            'usuario': usuario_atual
        })
        conn.commit()
        cursor.close()
        
        return True
    except Exception as e:
        print(f"Erro ao inserir log no sistema: {e}")
        if conn:
            cursor.close()
           
        return False

def inserir_log_alerta(ip_receptor, hostname_chamador, nome_usuario, nome_sala, status='Pendente', id_evento=None, observacoes=None):
    novo_id = obter_proximo_id(f'seq_botao_log_alerta')
    if not novo_id:
        print("Erro ao obter ID para log de alerta")
        return False
    
    conn = conectar_banco_de_dados()
    if not conn:
        print("Erro ao conectar com banco para log de alerta")
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {DATABASE_SCHEMA}.da_tbl_botao_log_alerta 
            (id, ip_receptor, hostname_chamador, nome_usuario, nome_sala, status, id_evento, observacoes) 
            VALUES (:id, :ip_receptor, :hostname_chamador, :nome_usuario, :nome_sala, :status, :id_evento, :observacoes)
        """, {
            'id': novo_id,
            'ip_receptor': ip_receptor,
            'hostname_chamador': hostname_chamador,
            'nome_usuario': nome_usuario,
            'nome_sala': nome_sala,
            'status': status,
            'id_evento': id_evento,
            'observacoes': observacoes
        })
        conn.commit()
        cursor.close()
        return novo_id
    except Exception as e:
        print(f"Erro ao inserir log de alerta: {e}")
        if conn:
            cursor.close()
        return False 