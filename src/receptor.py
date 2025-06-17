#!/usr/bin/env python3

import threading
import time
from flask import Flask, request, jsonify
import tkinter as tk
import json
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from pygame import mixer
import threading
import queue

import requests

app = Flask(__name__)

chave = 'alerta5656'
fila_alertas = queue.Queue()
thread_gui_ativa = False

@app.route('/check-health', methods=['GET'])
def check_health():
    return jsonify({"status": "ok"}), 200

@app.route(f'/{chave}/enviar', methods=['POST'])
def receber_mensagem():
    
    try:
        data = request.json
        if data['codigo'] == chave:
            fila_alertas.put((data['sala'], data['usuario']))
            
            global thread_gui_ativa
            if not thread_gui_ativa:
                thread_gui = threading.Thread(target=processar_alertas, daemon=True)
                thread_gui.start()
            
            return jsonify(True), 200
        else:
            print("Chave inválida")
    except Exception as e:
        print(f"Erro ao receber mensagem: {e}")
    return jsonify({"message": "Erro ao processar mensagem"}), 400

def processar_alertas():
    global thread_gui_ativa
    thread_gui_ativa = True
    
    while True:
        try:
            sala, usuario = fila_alertas.get(timeout=1)
            abrir_tela(sala, usuario)
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Erro ao processar alerta: {e}")

class Tela:
    def __init__(self, master, sala, usuario):
        self.master = master
        self.som_tocando = True 
        self.mixer_inicializado = False
        self.tempo_restante = 15
        
        self.master.title("Tela de Alerta")
        
       
        largura_tela = self.master.winfo_screenwidth()
        altura_tela = self.master.winfo_screenheight()
        
        fator_largura = largura_tela / 1920
        fator_altura = altura_tela / 1080
        fator_escala = min(fator_largura, fator_altura)
        
        fator_escala = max(0.5, min(fator_escala, 2.0))
        
        self.tela_pequena = largura_tela < 1024 or altura_tela < 768
        
        self.master.attributes('-fullscreen', True)
        
        self.master.protocol("WM_DELETE_WINDOW", self.nao_fechar)
        
        self.master.attributes('-topmost', True)
        
        self.master.focus_force()
        self.master.bind("<FocusOut>", self.manter_foco)
        
        botao_fonte = tkfont.Font(family="Arial", size=int(28 * fator_escala), weight="bold")
        icone_fonte = tkfont.Font(family="Arial", size=int(120 * fator_escala), weight="bold")
        texto_fonte = tkfont.Font(family="Arial", size=int(48 * fator_escala), weight="bold")
        sala_fonte = tkfont.Font(family="Helvetica", size=int(52 * fator_escala), weight="bold")
        local_fonte = tkfont.Font(family="Helvetica", size=int(45 * fator_escala), weight="bold")
        cronometro_fonte = tkfont.Font(family="Arial", size=int(36 * fator_escala), weight="bold")
        nome_usuario_fonte = tkfont.Font(family="Arial", size=int(36 * fator_escala), weight="bold")
        
        self.padding_top = int(20 * fator_escala)
        self.padding_medio = int(10 * fator_escala)
        self.padding_pequeno = int(5 * fator_escala)
        self.padding_botao = int(50 * fator_escala)
        
        self.frame = tk.Frame(self.master, bg="#B22222")
        self.frame.pack(expand=True, fill="both")

        self.cronometro_label = tk.Label(self.frame, text=f"Fechando em: {self.tempo_restante}s", 
                                        font=cronometro_fonte, fg="#FFD700", bg="#B22222")
        self.cronometro_label.pack(pady=(self.padding_top, self.padding_medio))

        self.icone_alerta = tk.Label(self.frame, text="⚠", font=icone_fonte, fg="#FFD700", bg="#B22222")
        self.icone_alerta.pack(pady=(self.padding_top, self.padding_top))

        if self.tela_pequena:
            texto_alerta = "ATENÇÃO!\nCÓDIGO VIOLETA!"
        else:
            texto_alerta = "ATENÇÃO!\n\nCODIGO VIOLETA!\n\n"
            
        self.texto_aviso = tk.Label(self.frame, text=texto_alerta, 
                                    font=texto_fonte, fg="white", bg="#B22222", justify="center")
        self.texto_aviso.pack(pady=(0, self.padding_medio))

        self.texto_sala = tk.Label(self.frame, text=f"LOCAL: {sala.upper()}", 
                                   font=local_fonte, fg="#000000", bg="#B22222", anchor="center")
        self.texto_sala.pack(pady=(0, self.padding_medio if self.tela_pequena else int(30 * fator_escala)))
        
        texto_usuario = f"Usuário: {usuario}" if self.tela_pequena else f"Nome do Usuário: {usuario}"
        self.nome_usuario_label = tk.Label(self.frame, text=texto_usuario, 
                                           font=nome_usuario_fonte, fg="white", bg="#B22222")
        self.nome_usuario_label.pack(pady=(0, self.padding_pequeno))
 
        botao_frame = tk.Frame(self.frame, bg="#B22222")
        botao_frame.pack(side="bottom", pady=(0, self.padding_botao))

        self.botao = tk.Button(botao_frame, text="AGUARDE...", font=botao_fonte,
                               bg="#666666", fg="white", activebackground="#666666",
                               activeforeground="white", relief=tk.FLAT,
                               command=self.tentar_fechar, 
                               padx=int(30 * fator_escala), pady=int(15 * fator_escala),
                               state="disabled")
        self.botao.pack()
        
        label_fonte = tkfont.Font(family="Arial", size=int(18 * fator_escala))
        self.label = tk.Label(self.frame, text="", 
                             font=label_fonte, bg="#B22222", fg="white")
        self.label.pack(pady=int(30 * fator_escala))

        self.piscar_contador = 0
        self.piscar()
        self.iniciar_cronometro()

        threading.Thread(target=self.tocar_som_inicial, daemon=True).start()

    def piscar(self):
        if self.piscar_contador < 8:  # 4 segundos (8 mudanças de 0.5 segundos)
            cor_atual = self.frame.cget("background")
            nova_cor = "#CD5C5C" if cor_atual == "#B22222" else "#B22222"
            self.frame.configure(background=nova_cor)
            self.cronometro_label.configure(bg=nova_cor)
            self.icone_alerta.configure(bg=nova_cor)
            self.texto_aviso.configure(bg=nova_cor)
            self.texto_sala.configure(bg=nova_cor)
            self.nome_usuario_label.configure(bg=nova_cor)
            self.label.configure(bg=nova_cor)
            self.piscar_contador += 1
            self.master.after(500, self.piscar)

    def iniciar_cronometro(self):
        """Inicia o cronômetro regressivo de 15 segundos"""
        self.atualizar_cronometro()

    def atualizar_cronometro(self):
        """Atualiza o cronômetro e fecha a janela quando chegar a 0"""
        if self.tempo_restante > 0:
            self.cronometro_label.config(text=f"Fechando em: {self.tempo_restante}s")
            self.tempo_restante -= 1
            self.master.after(1000, self.atualizar_cronometro)
        else:
            self.cronometro_label.config(text="Fechando...")
            self.fechar_aplicacao()

    def habilitar_botao_fechar(self):
        """Habilita o botão fechar após o som terminar"""
        self.som_tocando = False
        self.botao.config(text="FECHAR", bg="#c2c2c2", state="normal")
        self.label.config(text="")

    def tentar_fechar(self):
        """Tenta fechar a aplicação, só permite se o som terminou"""
        if not self.som_tocando:
            self.fechar_aplicacao()
        else:
            self.label.config(text="")

    def fechar_aplicacao(self):
        self.label.config(text="Fechando...")
        try:
            if self.mixer_inicializado:
                mixer.music.stop()
                mixer.quit()
        except:
            pass
        self.master.after(100, self.master.destroy)

    def nao_fechar(self):
        if self.som_tocando:
            self.label.config(text="")
        else:
            self.label.config(text="Use o botão FECHAR!")

    def manter_foco(self, event):
        self.master.focus_force()

    def tocar_som_inicial(self):
        try:
            mixer.init()
            self.mixer_inicializado = True
            mixer.music.load(r"C:\Botão_panico\sounds\alerta-sonoro.mp3")
            
            # Toca o som 4 vezes
            for i in range(4):
                mixer.music.play()
                while mixer.music.get_busy():
                    time.sleep(0.1)
                
                if i < 3:
                    time.sleep(0.5)
            
            self.master.after(0, self.habilitar_botao_fechar)
            
        except Exception as e:
            print(f"Erro ao tocar som: {e}")
            self.master.after(0, self.habilitar_botao_fechar)

def abrir_tela(sala, usuario):
    """Cria uma nova janela de alerta em uma thread separada"""
    def criar_janela():
        try:
            root = tk.Tk()
            app_tela = Tela(root, sala, usuario)
            root.mainloop()
        except Exception as e:
            print(f"Erro ao criar janela: {e}")
    
    thread_janela = threading.Thread(target=criar_janela, daemon=True)
    thread_janela.start()
    time.sleep(15)

if __name__ == "__main__":
    print("Iniciando servidor receptor...")
    
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=9090, debug=False), daemon=True)
    flask_thread.start()
    
    print("Servidor iniciado. Pressione Ctrl+C para sair.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
 
