#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DASHBOARD_ENV="$ROOT_DIR/dashboard/.env"
SERVER_ENV="$ROOT_DIR/src/.env"
HOSTNAMES_FILE="$ROOT_DIR/dashboard/hostnames.json"
ORACLE_DIR="$ROOT_DIR/docker/oracle/instantclient"
ORACLE_PACKAGES_DIR="$ROOT_DIR/docker/oracle/packages"
DEFAULT_ORACLE_ZIP_URL="https://download.oracle.com/otn_software/linux/instantclient/2326000/instantclient-basic-linux.x64-23.26.0.0.0.zip"
ORACLE_ZIP_URL="${ORACLE_ZIP_URL:-$DEFAULT_ORACLE_ZIP_URL}"
ORACLE_ZIP_PATH="${ORACLE_ZIP_PATH:-}"
REUSE_ENV_ONLY=0

if [[ -t 1 ]]; then
    COLOR_RESET=$'\033[0m'
    COLOR_RED=$'\033[31m'
    COLOR_GREEN=$'\033[32m'
    COLOR_YELLOW=$'\033[33m'
    COLOR_BLUE=$'\033[34m'
    COLOR_CYAN=$'\033[36m'
    COLOR_BOLD=$'\033[1m'
else
    COLOR_RESET=''
    COLOR_RED=''
    COLOR_GREEN=''
    COLOR_YELLOW=''
    COLOR_BLUE=''
    COLOR_CYAN=''
    COLOR_BOLD=''
fi

print_section() {
    printf '\n%s%s%s\n' "$COLOR_BOLD" "$1" "$COLOR_RESET"
}

log() {
    printf '%s[init]%s %s\n' "$COLOR_GREEN" "$COLOR_RESET" "$1"
}

fail() {
    printf '%s[init][erro]%s %s\n' "$COLOR_RED" "$COLOR_RESET" "$1" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "Comando obrigatorio nao encontrado: $1"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --reuse-env)
                REUSE_ENV_ONLY=1
                shift
                ;;
            --oracle-zip)
                [[ $# -ge 2 ]] || fail "Uso: --oracle-zip /caminho/arquivo.zip"
                ORACLE_ZIP_PATH="$2"
                shift 2
                ;;
            --oracle-url)
                [[ $# -ge 2 ]] || fail "Uso: --oracle-url https://..."
                ORACLE_ZIP_URL="$2"
                shift 2
                ;;
            -h|--help)
                cat <<'EOF'
Uso:
  ./scripts/init_linux.sh
  ./scripts/init_linux.sh --reuse-env
  ./scripts/init_linux.sh --oracle-zip /caminho/instantclient.zip
  ./scripts/init_linux.sh --oracle-url https://download.oracle.com/...zip

Opcoes:
  --reuse-env    Reutiliza dashboard/.env e src/.env sem novos prompts.
  --oracle-zip   Usa um arquivo ZIP local do Oracle Instant Client.
  --oracle-url   Sobrescreve a URL padrao de download do Instant Client.
EOF
                exit 0
                ;;
            *)
                fail "Argumento nao reconhecido: $1"
                ;;
        esac
    done
}

prompt_yes_no() {
    local var_name="$1"
    local prompt_text="$2"
    local default_value="${3:-s}"
    local answer=""

    read -r -p "${COLOR_YELLOW}${prompt_text}${COLOR_RESET} [${default_value}/n]: " answer
    answer="${answer:-$default_value}"
    answer="$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')"

    case "$answer" in
        s|sim|y|yes)
            printf -v "$var_name" 's'
            ;;
        n|nao|não|no)
            printf -v "$var_name" 'n'
            ;;
        *)
            fail "Resposta invalida: $answer"
            ;;
    esac
}

prompt_value() {
    local var_name="$1"
    local prompt_text="$2"
    local help_text="${3:-}"
    local example_value="${4:-}"
    local default_value="${5:-}"
    local current_value="${6:-}"
    local effective_default="$current_value"

    if [[ -z "$effective_default" ]]; then
        effective_default="$default_value"
    fi

    if [[ -n "$help_text" ]]; then
        printf '\n%s%s%s\n' "$COLOR_CYAN" "$help_text" "$COLOR_RESET"
    fi
    if [[ -n "$example_value" ]]; then
        printf '%sExemplo:%s %s\n' "$COLOR_BLUE" "$COLOR_RESET" "$example_value"
    fi

    local answer=""
    if [[ -n "$effective_default" ]]; then
        read -r -p "${COLOR_YELLOW}${prompt_text}${COLOR_RESET} [$effective_default]: " answer
        if [[ -z "$answer" ]]; then
            answer="$effective_default"
        fi
    else
        read -r -p "${COLOR_YELLOW}${prompt_text}${COLOR_RESET}: " answer
    fi

    printf -v "$var_name" '%s' "$answer"
}

prompt_secret() {
    local var_name="$1"
    local prompt_text="$2"
    local help_text="${3:-}"
    local example_value="${4:-}"
    local current_value="${5:-}"
    local answer=""

    if [[ -n "$help_text" ]]; then
        printf '\n%s%s%s\n' "$COLOR_CYAN" "$help_text" "$COLOR_RESET"
    fi
    if [[ -n "$example_value" ]]; then
        printf '%sExemplo:%s %s\n' "$COLOR_BLUE" "$COLOR_RESET" "$example_value"
    fi

    if [[ -n "$current_value" ]]; then
        read -r -s -p "${COLOR_YELLOW}${prompt_text}${COLOR_RESET} [manter atual]: " answer
        printf '\n'
        if [[ -z "$answer" ]]; then
            answer="$current_value"
        fi
    else
        read -r -s -p "${COLOR_YELLOW}${prompt_text}${COLOR_RESET}: " answer
        printf '\n'
    fi

    printf -v "$var_name" '%s' "$answer"
}

generate_secret_key() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32
    else
        date +%s | sha256sum | awk '{print $1}'
    fi
}

download_oracle_zip() {
    require_command mkdir
    mkdir -p "$ORACLE_PACKAGES_DIR"

    local target_zip="$ORACLE_PACKAGES_DIR/$(basename "$ORACLE_ZIP_URL")"
    log "Baixando Oracle Instant Client de $ORACLE_ZIP_URL"

    if command -v wget >/dev/null 2>&1; then
        wget -O "$target_zip" "$ORACLE_ZIP_URL"
    elif command -v curl >/dev/null 2>&1; then
        curl -L "$ORACLE_ZIP_URL" -o "$target_zip"
    else
        fail "Nem wget nem curl estao disponiveis para baixar o Instant Client"
    fi

    ORACLE_ZIP_PATH="$target_zip"
}

resolve_oracle_zip() {
    mkdir -p "$ORACLE_PACKAGES_DIR"

    if [[ -n "$ORACLE_ZIP_PATH" ]]; then
        [[ -f "$ORACLE_ZIP_PATH" ]] || fail "Arquivo ZIP informado nao encontrado: $ORACLE_ZIP_PATH"
        return
    fi

    local local_zip
    local_zip="$(find "$ORACLE_PACKAGES_DIR" -maxdepth 1 -type f -name 'instantclient-basic-linux*.zip' | head -n 1 || true)"

    if [[ -n "$local_zip" ]]; then
        print_section "Pacote Oracle Instant Client encontrado localmente"
        printf '%sArquivo:%s %s\n' "$COLOR_BLUE" "$COLOR_RESET" "$local_zip"
        prompt_yes_no USE_LOCAL_ZIP "Deseja usar o ZIP local existente?" "s"
        if [[ "$USE_LOCAL_ZIP" == "s" ]]; then
            ORACLE_ZIP_PATH="$local_zip"
            return
        fi
    fi

    print_section "Oracle Instant Client"
    printf '%sO Instant Client Linux e necessario para conectar neste Oracle 11g em thick mode.%s\n' "$COLOR_CYAN" "$COLOR_RESET"
    printf '%sURL padrao de download:%s %s\n' "$COLOR_BLUE" "$COLOR_RESET" "$ORACLE_ZIP_URL"
    prompt_yes_no DOWNLOAD_ORACLE_ZIP "Deseja baixar o ZIP oficial automaticamente agora?" "s"

    if [[ "$DOWNLOAD_ORACLE_ZIP" == "s" ]]; then
        download_oracle_zip
        return
    fi

    prompt_value ORACLE_ZIP_PATH \
        "Caminho local do ZIP do Oracle Instant Client" \
        "Informe um arquivo ZIP ja baixado manualmente se nao quiser baixar agora." \
        "/caminho/instantclient-basic-linux.x64-23.26.0.0.0.zip" \
        "" \
        "${ORACLE_ZIP_PATH:-}"

    [[ -f "$ORACLE_ZIP_PATH" ]] || fail "Arquivo ZIP informado nao encontrado: $ORACLE_ZIP_PATH"
}

extract_instant_client() {
    mkdir -p "$ORACLE_DIR"

    if [[ -f "$ORACLE_DIR/libclntsh.so" || -f "$ORACLE_DIR/libclntsh.so.23.1" ]]; then
        log "Instant Client Linux ja disponivel em docker/oracle/instantclient"
        return
    fi

    resolve_oracle_zip
    local zip_file="$ORACLE_ZIP_PATH"

    require_command unzip

    log "Extraindo Instant Client de $(basename "$zip_file")"
    local temp_dir
    temp_dir="$(mktemp -d)"
    unzip -oq "$zip_file" -d "$temp_dir"

    local extracted_dir
    extracted_dir="$(find "$temp_dir" -maxdepth 1 -mindepth 1 -type d -name 'instantclient_*' | head -n 1 || true)"
    [[ -n "$extracted_dir" ]] || fail "Nao foi possivel localizar a pasta extraida do Instant Client"

    rm -rf "$ORACLE_DIR"/*
    cp -a "$extracted_dir"/. "$ORACLE_DIR"/
    rm -rf "$temp_dir"

    [[ -f "$ORACLE_DIR/libclntsh.so" || -f "$ORACLE_DIR/libclntsh.so.23.1" ]] || fail "Instant Client extraido, mas bibliotecas principais nao foram encontradas"
}

write_env_files() {
    mkdir -p "$ROOT_DIR/dashboard" "$ROOT_DIR/src"

    cat > "$DASHBOARD_ENV" <<EOF
DATABASE_HOST=$DATABASE_HOST
DATABASE_USER=$DATABASE_USER
PASSWORD=$PASSWORD
DATABASE_PORT=$DATABASE_PORT
DATABASE_SERVICE=$DATABASE_SERVICE
DATABASE_SCHEMA=$DATABASE_SCHEMA
SERVER_IP=$SERVER_IP
SERVER_PORT=$SERVER_PORT
DASHBOARD_PORT=$DASHBOARD_PORT
ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient
PATH_EXE_BOTAO=$PATH_EXE_BOTAO
PATH_RECEPTOR=$PATH_RECEPTOR
DNS_SERVER=$DNS_SERVER
SECRET_KEY=$SECRET_KEY
EOF

    cat > "$SERVER_ENV" <<EOF
DATABASE_HOST=$DATABASE_HOST
DATABASE_USER=$DATABASE_USER
PASSWORD=$PASSWORD
DATABASE_PORT=$DATABASE_PORT
DATABASE_SERVICE=$DATABASE_SERVICE
DATABASE_SCHEMA=$DATABASE_SCHEMA
SERVER_PORT=$SERVER_PORT
ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient
EOF
}

bootstrap_files() {
    mkdir -p "$ROOT_DIR/dashboard/data/CACHE" "$ROOT_DIR/data/CACHE"

    if [[ ! -f "$HOSTNAMES_FILE" ]]; then
        printf '{}\n' > "$HOSTNAMES_FILE"
    fi
}

test_oracle_connection() {
    log "Testando conexao Oracle antes de subir os servicos"
    docker compose run --rm -T alert_server python - <<'PY'
import os
import sys
import traceback
import oracledb

def hint_for_error(message):
    message_upper = message.upper()

    if "DPI-1047" in message_upper:
        return "O Instant Client nao foi carregado corretamente. Verifique docker/oracle/instantclient e as bibliotecas .so."
    if "DPY-3010" in message_upper:
        return "Este Oracle exige thick mode. Verifique se o Instant Client foi inicializado."
    if "ORA-01017" in message_upper:
        return "Usuario ou senha invalidos no Oracle."
    if "ORA-12154" in message_upper:
        return "Service name/alias nao resolvido. Verifique DATABASE_SERVICE."
    if "ORA-12514" in message_upper:
        return "Listener nao reconhece o servico. Verifique DATABASE_SERVICE."
    if "ORA-12541" in message_upper:
        return "Nao foi possivel conectar ao listener. Verifique host, porta e firewall."
    if "ORA-12170" in message_upper or "TIMED OUT" in message_upper:
        return "Timeout de rede. Verifique conectividade entre o host Linux e o Oracle."
    return "Revise DATABASE_HOST, DATABASE_PORT, DATABASE_SERVICE, DATABASE_USER, PASSWORD e o Instant Client."

try:
    lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
    if lib_dir:
        oracledb.init_oracle_client(lib_dir=lib_dir)

    dsn = oracledb.makedsn(
        host=os.getenv("DATABASE_HOST"),
        port=int(os.getenv("DATABASE_PORT") or 1521),
        service_name=os.getenv("DATABASE_SERVICE"),
    )

    conn = oracledb.connect(
        user=os.getenv("DATABASE_USER"),
        password=os.getenv("PASSWORD"),
        dsn=dsn,
    )
    cur = conn.cursor()
    cur.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
    row = cur.fetchone()
    print(row[0] if row else "Conexao OK")
    cur.close()
    conn.close()
except Exception as exc:
    message = str(exc)
    print("Falha na conexao Oracle.", file=sys.stderr)
    print(f"Erro original: {message}", file=sys.stderr)
    print(f"Dica: {hint_for_error(message)}", file=sys.stderr)
    traceback.print_exc(limit=1, file=sys.stderr)
    raise SystemExit(1)
PY
}

load_existing_values() {
    if [[ -f "$DASHBOARD_ENV" ]]; then
        while IFS='=' read -r key value; do
            [[ -z "$key" ]] && continue
            [[ "$key" =~ ^# ]] && continue
            value="${value%$'\r'}"
            case "$key" in
                DATABASE_HOST|DATABASE_USER|PASSWORD|DATABASE_PORT|DATABASE_SERVICE|DATABASE_SCHEMA|SERVER_IP|SERVER_PORT|DASHBOARD_PORT|PATH_EXE_BOTAO|PATH_RECEPTOR|DNS_SERVER|SECRET_KEY)
                    printf -v "$key" '%s' "$value"
                    ;;
            esac
        done < "$DASHBOARD_ENV"
    fi
}

env_files_exist() {
    [[ -f "$DASHBOARD_ENV" && -f "$SERVER_ENV" ]]
}

collect_configuration() {
    local default_secret
    default_secret="$(generate_secret_key)"

    if [[ "$REUSE_ENV_ONLY" -eq 1 ]]; then
        env_files_exist || fail "Nao foi possivel usar --reuse-env porque dashboard/.env ou src/.env nao existem"
        print_section "Reutilizando configuracao existente"
        printf '%sUsando valores atuais de dashboard/.env e src/.env sem novos prompts.%s\n' "$COLOR_CYAN" "$COLOR_RESET"
        [[ -n "${DATABASE_HOST:-}" ]] || fail "DATABASE_HOST nao encontrado no .env atual"
        [[ -n "${DATABASE_USER:-}" ]] || fail "DATABASE_USER nao encontrado no .env atual"
        [[ -n "${PASSWORD:-}" ]] || fail "PASSWORD nao encontrado no .env atual"
        [[ -n "${DATABASE_SERVICE:-}" ]] || fail "DATABASE_SERVICE nao encontrado no .env atual"
        [[ -n "${DATABASE_SCHEMA:-}" ]] || fail "DATABASE_SCHEMA nao encontrado no .env atual"
        [[ -n "${SECRET_KEY:-}" ]] || fail "SECRET_KEY nao encontrado no .env atual"
        return
    fi

    if env_files_exist; then
        print_section "Configuracao existente encontrada"
        printf '%sJa existem arquivos dashboard/.env e src/.env.%s\n' "$COLOR_CYAN" "$COLOR_RESET"
        prompt_yes_no REUSE_CURRENT_ENV "Deseja reutilizar a configuracao atual sem preencher tudo de novo?" "s"
        if [[ "$REUSE_CURRENT_ENV" == "s" ]]; then
            [[ -n "${DATABASE_HOST:-}" ]] || fail "DATABASE_HOST nao encontrado no .env atual"
            [[ -n "${DATABASE_USER:-}" ]] || fail "DATABASE_USER nao encontrado no .env atual"
            [[ -n "${PASSWORD:-}" ]] || fail "PASSWORD nao encontrado no .env atual"
            [[ -n "${DATABASE_SERVICE:-}" ]] || fail "DATABASE_SERVICE nao encontrado no .env atual"
            [[ -n "${DATABASE_SCHEMA:-}" ]] || fail "DATABASE_SCHEMA nao encontrado no .env atual"
            [[ -n "${SECRET_KEY:-}" ]] || fail "SECRET_KEY nao encontrado no .env atual"
            return
        fi
    fi

    prompt_value DATABASE_HOST \
        "Oracle host" \
        "Endereco IP ou hostname do servidor Oracle usado pelo projeto." \
        "172.19.0.250" \
        "" \
        "${DATABASE_HOST:-}"
    prompt_value DATABASE_USER \
        "Oracle usuario" \
        "Usuario tecnico que o dashboard e o alert_server usarao para conectar no banco." \
        "bpuser" \
        "" \
        "${DATABASE_USER:-}"
    prompt_secret PASSWORD \
        "Oracle senha" \
        "Senha do usuario Oracle informado acima." \
        "sua_senha_aqui" \
        "${PASSWORD:-}"
    prompt_value DATABASE_PORT \
        "Oracle porta" \
        "Porta TCP do listener Oracle." \
        "1521" \
        "1521" \
        "${DATABASE_PORT:-}"
    prompt_value DATABASE_SERVICE \
        "Oracle service name" \
        "Service name publicado pela instancia Oracle." \
        "prdamevo" \
        "" \
        "${DATABASE_SERVICE:-}"
    prompt_value DATABASE_SCHEMA \
        "Oracle schema" \
        "Schema onde estao as tabelas do sistema Botao de Panico." \
        "dbasistemas" \
        "" \
        "${DATABASE_SCHEMA:-}"
    prompt_value SERVER_IP \
        "IP/hostname do alert_server para o dashboard" \
        "Endereco usado pelo dashboard para acessar o servidor principal de alertas. Em Docker Compose, use o nome do servico." \
        "alert_server" \
        "alert_server" \
        "${SERVER_IP:-}"
    prompt_value SERVER_PORT \
        "Porta do alert_server" \
        "Porta HTTP em que o servidor principal escuta os disparos de alerta." \
        "9600" \
        "9600" \
        "${SERVER_PORT:-}"
    prompt_value DASHBOARD_PORT \
        "Porta publica do dashboard" \
        "Porta exposta no host Linux para acessar a interface web do dashboard." \
        "3303" \
        "3303" \
        "${DASHBOARD_PORT:-}"
    prompt_value PATH_EXE_BOTAO \
        "Caminho do exe do botao no host/container" \
        "Caminho do executavel Windows do botao usado pelo dashboard ao copiar o cliente para maquinas remotas." \
        "/app/dist/botao_de_enviar.exe" \
        "/app/dist/botao_de_enviar.exe" \
        "${PATH_EXE_BOTAO:-}"
    prompt_value PATH_RECEPTOR \
        "Caminho do exe do receptor no host/container" \
        "Caminho do executavel Windows do receptor usado pelo dashboard ao instalar receptores via SMB." \
        "/app/dist/BotaoPanico_Receptor.exe" \
        "/app/dist/BotaoPanico_Receptor.exe" \
        "${PATH_RECEPTOR:-}"
    prompt_value DNS_SERVER \
        "DNS server" \
        "Servidor DNS interno usado em operacoes de rede e integracao com AD." \
        "172.19.0.10" \
        "172.19.0.10" \
        "${DNS_SERVER:-}"
    prompt_secret SECRET_KEY \
        "SECRET_KEY do dashboard" \
        "Chave secreta do Flask usada para sessao e criptografia de configuracoes do dashboard." \
        "troque-por-uma-chave-secreta-longa-e-unica" \
        "${SECRET_KEY:-$default_secret}"
}

main() {
    parse_args "$@"
    require_command docker
    docker compose version >/dev/null 2>&1 || fail "docker compose nao esta disponivel"

    load_existing_values
    collect_configuration

    print_section "Configuracao do Oracle Instant Client"
    printf '%sO script pode usar um ZIP local em docker/oracle/packages ou baixar automaticamente da Oracle.%s\n' "$COLOR_CYAN" "$COLOR_RESET"
    printf '%sURL padrao atual:%s %s\n' "$COLOR_BLUE" "$COLOR_RESET" "$ORACLE_ZIP_URL"

    [[ -n "$DATABASE_HOST" ]] || fail "DATABASE_HOST obrigatorio"
    [[ -n "$DATABASE_USER" ]] || fail "DATABASE_USER obrigatorio"
    [[ -n "$PASSWORD" ]] || fail "PASSWORD obrigatoria"
    [[ -n "$DATABASE_SERVICE" ]] || fail "DATABASE_SERVICE obrigatorio"
    [[ -n "$DATABASE_SCHEMA" ]] || fail "DATABASE_SCHEMA obrigatorio"
    [[ -n "$SECRET_KEY" ]] || fail "SECRET_KEY obrigatoria"

    bootstrap_files
    extract_instant_client
    write_env_files

    log "Construindo imagem do alert_server para validacao inicial"
    docker compose build alert_server >/dev/null
    test_oracle_connection

    log "Subindo containers"
    docker compose up -d --build

    log "Ambiente inicializado"
    printf '%sDashboard:%s http://localhost:%s\n' "$COLOR_GREEN" "$COLOR_RESET" "$DASHBOARD_PORT"
    printf '%sAlert server:%s http://localhost:%s/check-health\n' "$COLOR_GREEN" "$COLOR_RESET" "$SERVER_PORT"
}

main "$@"
