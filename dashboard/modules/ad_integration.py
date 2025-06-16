import ldap3
from modules.auth import descriptografar
from modules.database import conectar_banco_de_dados, DATABASE_SCHEMA

def obter_credenciais_ad():
    conn = conectar_banco_de_dados()
    if not conn:
        return None, None, None
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT usuario_ad, senha_ad, dominio
            FROM {DATABASE_SCHEMA}.da_tbl_botao_config_ad 
            WHERE id = 1
        """)
        
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if resultado:
            usuario_ad = resultado[0]
            senha_ad = descriptografar(resultado[1]) if resultado[1] else None
            dominio = resultado[2]
            return usuario_ad, senha_ad, dominio
        
        return None, None, None
    except Exception as e:
        print(f"Erro ao obter credenciais do AD: {e}")
        if conn:
            conn.close()
        return None, None, None

def consultar_hostnames_ad():
    usuario_ad, senha_ad, dominio = obter_credenciais_ad()
    
    if not usuario_ad or not senha_ad or not dominio:
        return False, "Credenciais do Active Directory não configuradas"
    
    try:
        server = ldap3.Server(dominio, get_info=ldap3.ALL)
        conn = ldap3.Connection(
            server,
            user=f"{usuario_ad}@{dominio}",
            password=senha_ad,
            auto_bind=True
        )
        
        base_dn = ','.join([f"DC={part}" for part in dominio.split('.')])
        filtro = '(&(objectClass=computer)(objectCategory=computer))'
        atributos = ['name', 'dNSHostName']
        
        conn.search(
            search_base=base_dn,
            search_filter=filtro,
            attributes=atributos
        )
        
        hostnames = []
        for entry in conn.entries:
            if hasattr(entry, 'name'):
                hostnames.append(entry.name.value.lower())
        
        conn.unbind()
        return True, hostnames
    except Exception as e:
        return False, str(e)

def consultar_usuarios_ad():
    usuario_ad, senha_ad, dominio = obter_credenciais_ad()
    
    if not usuario_ad or not senha_ad or not dominio:
        return False, "Credenciais do Active Directory não configuradas"
    
    try:
        server = ldap3.Server(dominio, get_info=ldap3.ALL)
        conn = ldap3.Connection(
            server,
            user=f"{usuario_ad}@{dominio}",
            password=senha_ad,
            auto_bind=True
        )
        
        base_dn = ','.join([f"DC={part}" for part in dominio.split('.')])
        
        filtro = '(objectClass=user)'
        atributos = ['sAMAccountName', 'displayName', 'cn', 'givenName', 'sn', 'mail', 'userAccountControl', 'objectCategory']
        
        conn.search(
            search_base=base_dn,
            search_filter=filtro,
            attributes=atributos,
            size_limit=1000
        )
        
        usuarios = []
        for entry in conn.entries:
            try:
                object_category = str(entry.objectCategory.value) if hasattr(entry, 'objectCategory') and entry.objectCategory.value else ""
                if 'person' not in object_category.lower():
                    continue
                
                user_account_control = entry.userAccountControl.value if hasattr(entry, 'userAccountControl') and entry.userAccountControl.value else 0
                
                if user_account_control & 2:
                    continue 
                
                username = entry.sAMAccountName.value if hasattr(entry, 'sAMAccountName') and entry.sAMAccountName.value else None
                nome_completo = entry.displayName.value if hasattr(entry, 'displayName') and entry.displayName.value else None
                
                if not nome_completo and hasattr(entry, 'cn') and entry.cn.value:
                    nome_completo = entry.cn.value
                
                if not nome_completo:
                    if hasattr(entry, 'givenName') and hasattr(entry, 'sn'):
                        primeiro_nome = entry.givenName.value if entry.givenName.value else ""
                        sobrenome = entry.sn.value if entry.sn.value else ""
                        nome_completo = f"{primeiro_nome} {sobrenome}".strip()
                
                if (username and nome_completo and 
                    len(username) > 1 and len(nome_completo) > 1 and
                    not username.lower().startswith(('$', 'krbtgt', 'guest', 'administrator')) and
                    not username.lower().endswith('$')):
                    
                    usuarios.append({
                        'username': username,
                        'nome_completo': nome_completo,
                        'email': entry.mail.value if hasattr(entry, 'mail') and entry.mail.value else None
                    })
            except Exception as entry_error:
                print(f"Erro ao processar entrada: {entry_error}")
                continue
        
        conn.unbind()
        return True, usuarios
        
    except ldap3.core.exceptions.LDAPInvalidFilterError as filter_error:
        return False, f"Filtro LDAP inválido: {filter_error}"
    except ldap3.core.exceptions.LDAPBindError as bind_error:
        return False, f"Erro de autenticação no AD: {bind_error}"
    except ldap3.core.exceptions.LDAPException as ldap_error:
        return False, f"Erro LDAP: {ldap_error}"
    except Exception as e:
        return False, f"Erro inesperado: {str(e)}" 