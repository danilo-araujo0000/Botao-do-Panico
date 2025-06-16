
-- Tabela de Salas
CREATE TABLE dbasistemas.da_tbl_botao_sala (
    id NUMBER(10) NOT NULL,
    nome_sala VARCHAR2(100) NOT NULL,
    hostname VARCHAR2(100) NOT NULL,
    status_instalacao VARCHAR2(100) DEFAULT 'Não Instalado',
    setor VARCHAR2(100),
    data_criacao DATE DEFAULT SYSDATE,
    data_atualizacao DATE DEFAULT SYSDATE,
    CONSTRAINT pk_botao_sala PRIMARY KEY (id)
);

CREATE SEQUENCE dbasistemas.seq_botao_sala
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;






-- Tabela de Usuários
CREATE TABLE dbasistemas.da_tbl_botao_usuario (
    id NUMBER(10) NOT NULL,
    nome_usuario VARCHAR2(100) NOT NULL,
    username VARCHAR2(50) NOT NULL,
    data_criacao DATE DEFAULT SYSDATE,
    data_atualizacao DATE DEFAULT SYSDATE,
    CONSTRAINT pk_botao_usuario PRIMARY KEY (id),
    CONSTRAINT uk_botao_usuario_username UNIQUE (username)
);

CREATE SEQUENCE dbasistemas.seq_botao_usuario
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;




-- Tabela de Receptores
CREATE TABLE dbasistemas.da_tbl_botao_receptor (
    id NUMBER(10) NOT NULL,
    ip_receptor VARCHAR2(15) NOT NULL,
    nome_receptor VARCHAR2(100),
    status_receptor VARCHAR2(100) DEFAULT 'Não Instalado',
    setor VARCHAR2(100),
    data_criacao DATE DEFAULT SYSDATE,
    data_atualizacao DATE DEFAULT SYSDATE,
    CONSTRAINT pk_botao_receptor PRIMARY KEY (id),
    CONSTRAINT uk_botao_receptor_ip UNIQUE (ip_receptor)
);

CREATE SEQUENCE dbasistemas.seq_botao_receptor
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;




-- Tabela de Logs de Alertas
CREATE TABLE dbasistemas.da_tbl_botao_log_alerta (
    id NUMBER(10) NOT NULL,
    ip_receptor VARCHAR2(15) NOT NULL,
    hostname_chamador VARCHAR2(100),
    nome_usuario VARCHAR2(100),
    nome_sala VARCHAR2(100),
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR2(20) DEFAULT 'nenhum',
    id_evento VARCHAR2(50),
    observacoes CLOB,
    CONSTRAINT pk_botao_log_alerta PRIMARY KEY (id)
);

CREATE SEQUENCE dbasistemas.seq_botao_log_alerta
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;



-- Tabela de Logs do Sistema
CREATE TABLE dbasistemas.da_tbl_botao_log_sistema (
    id NUMBER(10) NOT NULL,
    log CLOB NOT NULL,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    nivel VARCHAR2(20) DEFAULT 'INFO',
    modulo VARCHAR2(50),
    usuario VARCHAR2(50),
    CONSTRAINT pk_botao_log_sistema PRIMARY KEY (id)
);

CREATE SEQUENCE dbasistemas.seq_botao_log_sistema
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;




-- Tabela de Usuários de Login
CREATE TABLE dbasistemas.da_tbl_botao_usuario_login (
    id NUMBER(10) NOT NULL,
    usuario VARCHAR2(50) NOT NULL,
    senha VARCHAR2(255) NOT NULL,
    data_criacao DATE DEFAULT SYSDATE,
    CONSTRAINT pk_botao_usuario_login PRIMARY KEY (id),
    CONSTRAINT uk_botao_usuario_login_usuario UNIQUE (usuario),
);

CREATE SEQUENCE dbasistemas.seq_botao_usuario_login
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;


--tabela de configurações do AD
CREATE TABLE dbasistemas.da_tbl_botao_config_ad (
id NUMBER(10) PRIMARY KEY,
usuario_ad VARCHAR2(100) NOT NULL,
dominio VARCHAR2(100) NOT NULL,
senha_ad VARCHAR2(255) NOT NULL,
data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE dbasistemas.seq_botao_config_ad
START WITH 1
INCREMENT BY 1
NOCACHE
NOCYCLE

-- Tabela para configuração de sincronização automática 
CREATE TABLE dbasistemas.da_tbl_botao_sinc_user (
    id NUMBER(10) PRIMARY KEY,
    ativa NUMBER(1) DEFAULT 0 NOT NULL,
    tipo VARCHAR2(20) DEFAULT 'diario' NOT NULL,
    hora VARCHAR2(5) DEFAULT '02:00' NOT NULL,
    dia_semana NUMBER(1) DEFAULT 0,
    dia_mes NUMBER(2) DEFAULT 1,
    ultima_execucao TIMESTAMP,
    proxima_execucao TIMESTAMP,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);


-- Comentários
COMMENT ON TABLE dbasistemas.da_tbl_botao_sala IS 'Tabela de mapeamento de salas do sistema "botão do pânico"';
COMMENT ON TABLE dbasistemas.da_tbl_botao_usuario IS 'Tabela de usuários do sistema "botão do pânico"';
COMMENT ON TABLE dbasistemas.da_tbl_botao_receptor IS 'Tabela de receptores de alertas do sistema "botão do pânico"';
COMMENT ON TABLE dbasistemas.da_tbl_botao_log_alerta IS 'Tabela de logs de alertas disparados do sistema "botão do pânico"';
COMMENT ON TABLE dbasistemas.da_tbl_botao_log_sistema IS 'Tabela de logs de sistema "botão do pânico"';
COMMENT ON TABLE dbasistemas.da_tbl_botao_usuario_login IS 'Tabela de usuários para autenticação do sistema "botão do pânico"';
COMMENT ON TABLE dbasistemas.da_tbl_botao_config_ad IS 'Tabela de configurações do AD SERVER para o sistema "botão do pânico"';


-- Criar Usuario de Acesso as tabelas
CREATE USER bpuser IDENTIFIED BY bpuser;
GRANT CONNECT TO bpuser;

GRANT ALTER, INSERT, UPDATE, DELETE ON dbasistemas.da_tbl_botao_sala TO bpuser;
GRANT ALTER, INSERT, UPDATE, DELETE ON dbasistemas.da_tbl_botao_usuario TO bpuser;
GRANT ALTER, INSERT, UPDATE, DELETE ON dbasistemas.da_tbl_botao_receptor TO bpuser;
GRANT ALTER, INSERT, UPDATE, DELETE ON dbasistemas.da_tbl_botao_log_alerta TO bpuser;
GRANT ALTER, INSERT, UPDATE, DELETE ON dbasistemas.da_tbl_botao_log_sistema TO bpuser;
GRANT ALTER, INSERT, UPDATE, DELETE ON dbasistemas.da_tbl_botao_usuario_login TO bpuser;
GRANT ALTER, INSERT, UPDATE, DELETE ON dbasistemas.da_tbl_botao_config_ad TO bpuser;
GRANT ALTER, INSERT, UPDATE, DELETE ON dbasistemas.da_tbl_botao_sinc_user TO bpuser;
GRANT SELECT, ALTER ON dbasistemas.seq_botao_config_ad TO bpuser;
GRANT SELECT, ALTER ON dbasistemas.seq_botao_sala TO bpuser;
GRANT SELECT, ALTER ON dbasistemas.seq_botao_usuario TO bpuser;
GRANT SELECT, ALTER ON dbasistemas.seq_botao_receptor TO bpuser;
GRANT SELECT, ALTER ON dbasistemas.seq_botao_log_alerta TO bpuser;
GRANT SELECT, ALTER ON dbasistemas.seq_botao_log_sistema TO bpuser;
GRANT SELECT, ALTER ON dbasistemas.seq_botao_usuario_login TO bpuser;
GRANT SELECT, ALTER ON dbasistemas.seq_botao_config_ad TO bpuser;







