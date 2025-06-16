from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from modules.auth import verificar_credenciais
from modules.logging_utils import inserir_log_sistema

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        
        if verificar_credenciais(usuario, senha):
            session['usuario_logado'] = usuario
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('main.inicio'))
        else:
            inserir_log_sistema(f'Tentativa de login inválida para usuário: {usuario}', 'WARNING', 'LOGIN')
            flash('Usuário ou senha incorretos!', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    usuario = session.get('usuario_logado', 'DESCONHECIDO')
    session.pop('usuario_logado', None)
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('auth.login')) 