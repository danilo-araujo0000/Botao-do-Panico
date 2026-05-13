FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient \
    LD_LIBRARY_PATH=/opt/oracle/instantclient \
    PATH_EXE_BOTAO=/app/dist/botao_de_enviar.exe \
    PATH_RECEPTOR=/app/dist/BotaoPanico_Receptor.exe

RUN apt-get update && apt-get install -y --no-install-recommends \
    dnsutils \
    libaio1 \
    libnsl2 \
    libkrb5-3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY docker/requirements-linux.txt /tmp/requirements-linux.txt
RUN python -m pip install --upgrade pip && \
    pip install -r /tmp/requirements-linux.txt

COPY . /app

RUN mkdir -p /opt/oracle/instantclient

CMD ["python", "-u", "dashboard/app.py"]
