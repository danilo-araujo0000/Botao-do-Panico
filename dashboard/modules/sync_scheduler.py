import json
import threading
import time
from datetime import datetime, timedelta
from modules.database import conectar_banco_de_dados, DATABASE_SCHEMA
from modules.ad_integration import consultar_usuarios_ad
from modules.logging_utils import inserir_log_sistema
from modules.database import obter_proximo_id

scheduler_thread = None
scheduler_running = False

def executar_sincronizacao_usuarios():
    try:
        inserir_log_sistema("Iniciando sincronização automática de usuários do AD", "INFO", "SYNC")
        
        sucesso, usuarios_ad = consultar_usuarios_ad()
        if not sucesso:
            inserir_log_sistema(f"Erro ao consultar usuários do AD: {usuarios_ad}", "ERROR", "SYNC")
            return False
        
        conn = conectar_banco_de_dados()
        if not conn:
            inserir_log_sistema("Erro ao conectar ao banco de dados para sincronização", "ERROR", "SYNC")
            return False
        
        try:
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT username FROM {DATABASE_SCHEMA}.da_tbl_botao_usuario")
            usuarios_existentes = [row[0].upper() for row in cursor.fetchall()]
            
            usuarios_novos = [
                usuario for usuario in usuarios_ad 
                if usuario.get('username', '').upper() not in usuarios_existentes
            ]
            
            importados = 0
            for usuario in usuarios_novos:
                username = usuario.get('username', '').upper()
                nome_completo = usuario.get('nome_completo', '')
                
                if username and nome_completo:
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
            
            cursor.execute(f"""
                UPDATE {DATABASE_SCHEMA}.da_tbl_botao_sinc_user 
                SET ultima_execucao = CURRENT_TIMESTAMP
                WHERE id = 1
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            inserir_log_sistema(f"Sincronização automática concluída: {importados} usuários importados", "INFO", "SYNC")
            return True
            
        except Exception as e:
            conn.rollback()
            if conn:
                conn.close()
            inserir_log_sistema(f"Erro durante sincronização: {str(e)}", "ERROR", "SYNC")
            return False
            
    except Exception as e:
        inserir_log_sistema(f"Erro na sincronização automática: {str(e)}", "ERROR", "SYNC")
        return False

def calcular_proxima_execucao(config):
    agora = datetime.now()
    hora_parts = config['hora'].split(':')
    hora = int(hora_parts[0])
    minuto = int(hora_parts[1])
    
    if config['tipo'] == 'diario':
        proxima = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if proxima <= agora:
            proxima += timedelta(days=1)
    
    elif config['tipo'] == 'semanal':
        dia_semana = int(config['dia_semana'])
        dias_ate_proximo = (dia_semana - agora.weekday()) % 7
        if dias_ate_proximo == 0:
            proxima = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
            if proxima <= agora:
                dias_ate_proximo = 7
        
        if dias_ate_proximo > 0:
            proxima = agora + timedelta(days=dias_ate_proximo)
            proxima = proxima.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    
    elif config['tipo'] == 'mensal':
        dia_mes = int(config['dia_mes'])
        try:
            proxima = agora.replace(day=dia_mes, hour=hora, minute=minuto, second=0, microsecond=0)
            if proxima <= agora:
                if agora.month == 12:
                    proxima = proxima.replace(year=agora.year + 1, month=1)
                else:
                    proxima = proxima.replace(month=agora.month + 1)
        except ValueError:
            if agora.month == 12:
                proxima = datetime(agora.year + 1, 1, min(dia_mes, 28), hora, minuto)
            else:
                import calendar
                ultimo_dia = calendar.monthrange(agora.year, agora.month + 1)[1]
                proxima = datetime(agora.year, agora.month + 1, min(dia_mes, ultimo_dia), hora, minuto)
    
    return proxima

def atualizar_proxima_execucao(config):
    try:
        proxima = calcular_proxima_execucao(config)
        
        conn = conectar_banco_de_dados()
        if conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE {DATABASE_SCHEMA}.da_tbl_botao_sinc_user 
                SET proxima_execucao = :proxima_execucao
                WHERE id = 1
            """, {'proxima_execucao': proxima})
            conn.commit()
            cursor.close()
            conn.close()
    except Exception as e:
        inserir_log_sistema(f"Erro ao atualizar próxima execução: {str(e)}", "ERROR", "SYNC")

def scheduler_loop():
    global scheduler_running
    
    while scheduler_running:
        try:
            conn = conectar_banco_de_dados()
            if conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT ativa, tipo, hora, dia_semana, dia_mes, proxima_execucao
                    FROM {DATABASE_SCHEMA}.da_tbl_botao_sinc_user 
                    WHERE id = 1
                """)
                
                resultado = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if resultado and resultado[0]:  # Se ativa
                    config = {
                        'ativa': bool(resultado[0]),
                        'tipo': resultado[1],
                        'hora': resultado[2],
                        'dia_semana': resultado[3],
                        'dia_mes': resultado[4],
                        'proxima_execucao': resultado[5]
                    }
                    
                    agora = datetime.now()
                    
                    if config['proxima_execucao'] and agora >= config['proxima_execucao']:
                        executar_sincronizacao_usuarios()
                        atualizar_proxima_execucao(config)
                    elif not config['proxima_execucao']:
                        atualizar_proxima_execucao(config)
            
            time.sleep(60)  # Verifica a cada minuto
            
        except Exception as e:
            inserir_log_sistema(f"Erro no scheduler de sincronização: {str(e)}", "ERROR", "SYNC")
            time.sleep(60)

def iniciar_scheduler():
    global scheduler_thread, scheduler_running
    
    if scheduler_thread and scheduler_thread.is_alive():
        return
    
    scheduler_running = True
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    inserir_log_sistema("Scheduler de sincronização iniciado", "INFO", "SYNC")

def parar_scheduler():
    global scheduler_running
    scheduler_running = False
    inserir_log_sistema("Scheduler de sincronização parado", "INFO", "SYNC")

def atualizar_agendamento_sincronizacao():
    try:
        conn = conectar_banco_de_dados()
        if conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT ativa, tipo, hora, dia_semana, dia_mes
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
                    'dia_mes': resultado[4]
                }
                
                if config['ativa']:
                    atualizar_proxima_execucao(config)
                    if not scheduler_running:
                        iniciar_scheduler()
                else:
                    parar_scheduler()
    except Exception as e:
        inserir_log_sistema(f"Erro ao atualizar agendamento: {str(e)}", "ERROR", "SYNC") 
        
#função para guardar em um arquivo os hostnames que estao no Banco de Dados
def guardar_hostnames_no_arquivo():
    try:
        inserir_log_sistema("Iniciando guardar hostnames no arquivo", "INFO", "HOSTNAMES")
        conn = conectar_banco_de_dados()
        if not conn:
            inserir_log_sistema("Falha ao conectar ao banco de dados", "ERROR", "HOSTNAMES")
            return False
        cursor = conn.cursor()
        cursor.execute(f"SELECT hostname, nome_sala FROM {DATABASE_SCHEMA}.da_tbl_botao_sala")
        hostnames = cursor.fetchall()
        cursor.close()
        conn.close()
        
        hostnames_dict = {row[0]: row[1] for row in hostnames}
        
        with open('hostnames.json', 'w', encoding='utf-8') as file:
            json.dump(hostnames_dict, file, indent=4, ensure_ascii=False)
        inserir_log_sistema(f"Hostnames guardados: {len(hostnames_dict)} registros", "INFO", "HOSTNAMES")
        return True
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        inserir_log_sistema(f"Erro ao guardar hostnames: {str(e)}", "ERROR", "HOSTNAMES")
        return False

def scheduler_hostnames_loop():
    inserir_log_sistema("Loop do scheduler de hostnames iniciado", "INFO", "HOSTNAMES")
    while True:
        guardar_hostnames_no_arquivo()
        tempo_em_horas = 4
        tempo_em_segundos = tempo_em_horas * 3600
        time.sleep(tempo_em_segundos)

def iniciar_scheduler_hostnames():
    inserir_log_sistema("Scheduler de hostnames iniciado", "INFO", "HOSTNAMES")
    threading.Thread(target=scheduler_hostnames_loop, daemon=True).start()

