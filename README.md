# Botao de Panico

Sistema interno de alerta com tres componentes principais:

- `src/server.py`: servidor Flask que recebe um disparo e redistribui o alerta para os receptores cadastrados
- `src/receptor.py`: receptor local que exibe alerta visual/sonoro
- `dashboard/`: painel web para cadastro, operacao e logs

## Arquitetura

- `dashboard` consulta Oracle e administra salas, usuarios e receptores
- `alert_server` recebe `POST /alerta5656/enviar`
- cada receptor escuta em `:9090`
- o banco Oracle guarda cadastros e logs

## Requisitos

- Docker e Docker Compose
- Oracle acessivel pela aplicacao
- Oracle Instant Client disponivel no host ou montado no container

## Configuracao

Crie os arquivos:

- `dashboard/.env`
- `src/.env`

Use como base:

- [dashboard/.env.example](/home/apps/botao/dashboard/.env.example)
- [src/.env.example](/home/apps/botao/src/.env.example)

## Subir com Docker

```bash
docker compose up -d --build
```

Servicos:

- Dashboard: `http://localhost:3303`
- Alert server: `http://localhost:9600`

## Banco de dados

O script base de criacao esta em:

- [create_tables_oracle_simple.sql](/home/apps/botao/dashboard/sql/create_tables_oracle_simple.sql)

Para a funcionalidade de ativar/desativar receptores em ambientes existentes, aplique:

```sql
ALTER TABLE dbasistemas.da_tbl_botao_receptor
ADD ativo NUMBER(1) DEFAULT 1 NOT NULL;

UPDATE dbasistemas.da_tbl_botao_receptor
SET ativo = 1
WHERE ativo IS NULL;

ALTER TABLE dbasistemas.da_tbl_botao_receptor
ADD CONSTRAINT ck_botao_receptor_ativo
CHECK (ativo IN (0, 1));

COMMIT;
```

## Publicacao no GitHub

Antes do push:

- nao versionar `.env`
- nao versionar caches e arquivos gerados
- preencher segredos reais apenas no ambiente de execucao
- revisar se executaveis em `dist/` devem ficar fora do repositorio
