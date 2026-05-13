from server import conectar_banco_de_dados ,  obter_proximo_id
from gerar_senhas_hash import criptografar_senha
import time

conn = conectar_banco_de_dados()

def inserir_usuarios():
    senha = criptografar_senha('botao@2025')
    proximo_id = obter_proximo_id('dbasistemas.seq_botao_usuario_login')
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO dbasistemas.da_tbl_botao_usuario_login (id, usuario, senha) VALUES ({proximo_id}, 'Administrador', '{senha}')")
    conn.commit()
    cursor.close()
    time.sleep(1)
    print("🔍 Verificando se o usuário foi inserido")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM dbasistemas.da_tbl_botao_usuario_login WHERE usuario = 'Administrador'")
    resultado = cursor.fetchone()
    cursor.close()
    if resultado:
        print("✅Usuário inserido com sucesso")
        print(f"dados obtidos: {resultado}")
    else:
        print("❌Erro ao inserir usuário")





inserir_usuarios()