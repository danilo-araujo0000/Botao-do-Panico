from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from datetime import datetime, timedelta
import oracledb
from modules.auth import login_required
from modules.database import conectar_banco_de_dados, DATABASE_SCHEMA
from modules.utils import verificar_status_servidor

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'usuario_logado' in session:
        return redirect(url_for('main.inicio'))
    return redirect(url_for('auth.login'))

@main_bp.route('/botao/dashboard')
@login_required
def inicio():
    conn = conectar_banco_de_dados()
    if not conn:
        flash('Erro ao conectar com o banco de dados', 'error')
        return render_template('erro.html')
    
    try:
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT COUNT(*) as total FROM {DATABASE_SCHEMA}.da_tbl_botao_sala")
        total_salas = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) as total FROM {DATABASE_SCHEMA}.da_tbl_botao_usuario")
        total_usuarios = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) as total FROM {DATABASE_SCHEMA}.da_tbl_botao_receptor")
        total_receptores = cursor.fetchone()[0]
        
        cursor.execute(f"""
            SELECT * FROM (
                SELECT nome_sala, nome_usuario, data_hora, id_evento,
                       COUNT(*) as total_receptores,
                       SUM(CASE WHEN status = 'Enviado' THEN 1 ELSE 0 END) as enviados_sucesso
                FROM {DATABASE_SCHEMA}.da_tbl_botao_log_alerta 
                GROUP BY id_evento, nome_sala, nome_usuario, data_hora
                ORDER BY data_hora DESC
            ) WHERE ROWNUM <= 5
        """)
        ultimos_acionamentos_raw = cursor.fetchall()
        
        ultimos_acionamentos = []
        for row in ultimos_acionamentos_raw:
            ultimos_acionamentos.append({
                'nome_sala': row[0],
                'nome_usuario': row[1], 
                'data_hora': row[2],
                'id_evento': row[3],
                'total_receptores': row[4],
                'enviados_sucesso': row[5]
            })
        
        cursor.execute(f"""
            SELECT * FROM (
                SELECT log, data_hora 
                FROM {DATABASE_SCHEMA}.da_tbl_botao_log_sistema 
                ORDER BY data_hora DESC
            ) WHERE ROWNUM <= 10
        """)
        ultimos_logs_raw = cursor.fetchall()
        
        ultimos_logs = []
        for row in ultimos_logs_raw:
            ultimos_logs.append({
                'log': row[0],
                'data_hora': row[1]
            })
        
        status_servidor = verificar_status_servidor()
        
        cursor.close()
        
        return render_template('inicio.html', 
                             total_salas=total_salas,
                             total_usuarios=total_usuarios,
                             total_receptores=total_receptores,
                             ultimos_acionamentos=ultimos_acionamentos,
                             ultimos_logs=ultimos_logs,
                             status_servidor=status_servidor)
    
    except Exception as e:
        print(f"Erro na função inicio: {e}")
        flash('Erro ao carregar dados do dashboard', 'error')
        if conn:
            conn.close()
        return render_template('erro.html')

@main_bp.route('/salas')
@login_required
def salas():
    conn = conectar_banco_de_dados()
    if not conn:
        flash('Erro ao conectar com o banco de dados', 'error')
        return render_template('erro.html')
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, nome_sala, hostname, setor, status_instalacao FROM {DATABASE_SCHEMA}.da_tbl_botao_sala ORDER BY nome_sala")
        salas_raw = cursor.fetchall()
        
        salas_list = []
        for row in salas_raw:
            salas_list.append({
                'id': row[0],
                'nome_sala': row[1],
                'hostname': row[2],
                'setor': row[3],
                'status_instalacao': row[4] if row[4] else 'Não verificado'
            })
        
        cursor.close()
        
        return render_template('salas.html', salas=salas_list)
    
    except Exception as e:
        print(f"Erro ao carregar salas: {e}")
        flash('Erro ao carregar dados das salas', 'error')
        if conn:
            conn.close()
        return render_template('erro.html')

@main_bp.route('/usuarios')
@login_required
def usuarios():
    conn = conectar_banco_de_dados()
    if not conn:
        flash('Erro ao conectar com o banco de dados', 'error')
        return render_template('erro.html')
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, nome_usuario, username FROM {DATABASE_SCHEMA}.da_tbl_botao_usuario ORDER BY nome_usuario")
        usuarios_raw = cursor.fetchall()
        
        usuarios_list = []
        for row in usuarios_raw:
            usuarios_list.append({
                'id': row[0],
                'nome_usuario': row[1],
                'USERNAME': row[2]  
            })
        
        cursor.close()
        
        return render_template('usuarios.html', usuarios=usuarios_list)
    
    except Exception as e:
        print(f"Erro ao carregar usuários: {e}")
        flash('Erro ao carregar dados dos usuários', 'error')
        if conn:
            conn.close()
        return render_template('erro.html')

@main_bp.route('/receptores')
@login_required
def receptores():
    conn = conectar_banco_de_dados()
    if not conn:
        flash('Erro ao conectar com o banco de dados', 'error')
        return render_template('erro.html')
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, ip_receptor, nome_receptor, setor, status_receptor FROM {DATABASE_SCHEMA}.da_tbl_botao_receptor ORDER BY ip_receptor")
        receptores_raw = cursor.fetchall()
        
        receptores_list = []
        for row in receptores_raw:
            receptores_list.append({
                'id': row[0],
                'ip_receptor': row[1],
                'nome_receptor': row[2],
                'setor': row[3],
                'status_receptor': row[4] if row[4] else 'Não verificado'
            })
        
        cursor.close()
        
        return render_template('receptores.html', receptores=receptores_list)
    
    except Exception as e:
        print(f"Erro ao carregar receptores: {e}")
        flash('Erro ao carregar dados dos receptores', 'error')
        if conn:
            conn.close()
        return render_template('erro.html')

@main_bp.route('/logs/botao_panico')
@login_required
def logs():
    dias = request.args.get('dias', '7')
    tipo = request.args.get('tipo', 'todos')
    
    try:
        dias_int = int(dias)
    except (ValueError, TypeError):
        dias_int = 7
    
    data_inicio = datetime.now() - timedelta(days=dias_int)
    
    conn = None
    cursor = None
    try:
        conn = conectar_banco_de_dados()
        if not conn:
            raise oracledb.Error("Falha ao obter conexão do banco de dados.")
            
        cursor = conn.cursor()
        
        logs_sistema = []
        logs_alertas = []
        
        if tipo in ['todos', 'sistema']:
            cursor.execute(f"""
                SELECT log, data_hora 
                FROM {DATABASE_SCHEMA}.da_tbl_botao_log_sistema 
                WHERE data_hora >= :data_inicio 
                ORDER BY data_hora DESC
            """, {'data_inicio': data_inicio})
            
            cols_sistema = [desc[0].lower() for desc in cursor.description]
            for row in cursor.fetchall():
                log_dict = dict(zip(cols_sistema, row))
                
                if 'log' in log_dict and isinstance(log_dict['log'], oracledb.LOB):
                    log_dict['log'] = log_dict['log'].read()
                
                logs_sistema.append(log_dict)
        
        if tipo in ['todos', 'alertas']:
            cursor.execute(f"""
                SELECT ip_receptor, hostname_chamador, nome_usuario, nome_sala, 
                       data_hora, status, id_evento 
                FROM {DATABASE_SCHEMA}.da_tbl_botao_log_alerta 
                WHERE data_hora >= :data_inicio 
                ORDER BY data_hora DESC
            """, {'data_inicio': data_inicio})
            
            cols_alertas = [desc[0].lower() for desc in cursor.description]
            for row in cursor.fetchall():
                logs_alertas.append(dict(zip(cols_alertas, row)))
        
        return render_template('botaologs.html', 
                               logs_sistema=logs_sistema,
                               logs_alertas=logs_alertas,
                               dias_selecionado=dias,
                               tipo_selecionado=tipo)
    
    except oracledb.Error as e:
        print(f"Erro de banco de dados ao carregar logs: {e}")
        flash('Erro de banco de dados ao carregar dados dos logs', 'error')
        return render_template('erro.html')
    except Exception as e:
        print(f"Erro inesperado ao carregar logs: {e}")
        flash('Ocorreu um erro inesperado ao processar sua solicitação', 'error')
        return render_template('erro.html')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@main_bp.route('/configuracoes')
@login_required
def configuracoes():
    conn = conectar_banco_de_dados()
    usuarios_login = []
    config_ad = None
    
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT id, usuario, data_criacao
                FROM {DATABASE_SCHEMA}.da_tbl_botao_usuario_login 
                ORDER BY usuario
            """)
            
            resultados = cursor.fetchall()
            for row in resultados:
                usuarios_login.append({
                    'id': row[0],
                    'usuario': row[1],
                    'data_criacao': row[2]
                })
            
            cursor.execute(f"""
                SELECT usuario_ad, dominio
                FROM {DATABASE_SCHEMA}.da_tbl_botao_config_ad 
                WHERE id = 1
            """)
            
            resultado_ad = cursor.fetchone()
            if resultado_ad:
                config_ad = {
                    'ad_usuario': resultado_ad[0],
                    'ad_dominio': resultado_ad[1]
                }
            
            cursor.close()
        except Exception as e:
            print(f"Erro ao buscar dados: {e}")
            if conn:
                conn.close()
    
    return render_template('configuracoes.html', usuarios=usuarios_login, config=config_ad) 