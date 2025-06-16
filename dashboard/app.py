#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask
from config import SECRET_KEY, SESSION_COOKIE_SECURE
from routes.auth_routes import auth_bp
from routes.main_routes import main_bp
from routes.api_routes import api_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)

try:
    from modules.sync_scheduler import iniciar_scheduler
    iniciar_scheduler()
except Exception as e:
    print(f"Erro ao iniciar scheduler de sincronização: {e}")

if __name__ == '__main__':
    app.run( host='0.0.0.0', port=3303 , use_reloader=False , debug=False)