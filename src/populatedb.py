from server import conectar_banco_de_dados, obter_proximo_id, database_schema
from gerar_senhas_hash import criptografar_senha
import time

conn = conectar_banco_de_dados()

def inserir_usuarios():
    senha = criptografar_senha('botao@2025')
    proximo_id = obter_proximo_id('seq_botao_usuario_login')
    if proximo_id is None:
        raise RuntimeError("Nao foi possivel obter o proximo ID da sequence seq_botao_usuario_login")
    cursor = conn.cursor()
    cursor.execute(
        f"""
        INSERT INTO {database_schema}.da_tbl_botao_usuario_login (id, usuario, senha)
        VALUES (:id, :usuario, :senha)
        """,
        id=proximo_id,
        usuario='Administrador',
        senha=senha,
    )
    conn.commit()
    cursor.close()
    time.sleep(1)
    print("🔍 Verificando se o usuário foi inserido")
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT * FROM {database_schema}.da_tbl_botao_usuario_login WHERE usuario = :usuario",
        usuario='Administrador',
    )
    resultado = cursor.fetchone()
    cursor.close()
    if resultado:
        print("✅Usuário inserido com sucesso")
        print(f"dados obtidos: {resultado}")
    else:
        print("❌Erro ao inserir usuário")





inserir_usuarios()
