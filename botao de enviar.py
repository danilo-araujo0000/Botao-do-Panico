import requests
import time
import os
import getpass
import tkinter as tk
import json
import socket




server = "172.19.200.1"
chave = "alerta5656"


def enviar_mensagem():
    global usuario_windows
    
    hostname = socket.gethostname()
    usuario_windows = getpass.getuser().upper()
    mostrar_tela_enviado()
    
    mensagem = {
        'hostname': hostname,
        'usuario': usuario_windows,
        'codigo': 'alerta5656'
    }
    
    print(f"Enviando mensagem: {mensagem}")

  
    requests.post(f"http://{server}:9600/{chave}/enviar", json=mensagem)
      


def mostrar_tela_enviado():
    root = tk.Tk()
    root.overrideredirect(True)  
    root.geometry("300x200+{}+{}".format(
        int(root.winfo_screenwidth()/2 - 150),
        int(root.winfo_screenheight()/2 - 100)
    ))
    root.configure(bg='#ffffff') 

    frame = tk.Frame(root, bg='#ffffff')
    frame.place(relx=0.5, rely=0.5, anchor='center')

    label = tk.Label(frame, text="Enviada!", font=("Arial", 16, "bold"), bg='#ffffff', fg='#2ecc71')
    label.pack()

    check = tk.Label(frame, text="✓", font=("Arial", 48), bg='#ffffff', fg='#2ecc71')
    check.pack(pady=10)

    def fechar_janela():
        root.destroy()

    root.after(2000, fechar_janela)
    root.mainloop()

def mostrar_tela_erro():
    root = tk.Tk()
    root.overrideredirect(True)  
    root.geometry("300x200+{}+{}".format(
        int(root.winfo_screenwidth()/2 - 150),
        int(root.winfo_screenheight()/2 - 100)
    ))
    root.configure(bg='#ffffff') 

    frame = tk.Frame(root, bg='#ffffff')
    frame.place(relx=0.5, rely=0.5, anchor='center')

    label = tk.Label(frame, text="Erro ao enviar!", font=("Arial", 16, "bold"), bg='#ffffff', fg='#e74c3c')
    label.pack()

    error_icon = tk.Label(frame, text="X", font=("Arial", 24, "bold"), bg='#ffffff', fg='#e74c3c')
    error_icon.pack(pady=10)

    def fechar_janela():
        root.destroy()

    root.after(3000, fechar_janela)
    root.mainloop()

if __name__ == "__main__":
     enviar_mensagem()
     print(f"usuario_windows: {usuario_windows}")
     
