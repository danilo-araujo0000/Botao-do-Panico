#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import bcrypt

def criptografar_senha(senha):
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')



