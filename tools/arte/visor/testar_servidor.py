"""Sobe o servir.py, confere o que ele entrega e o que recusa, e derruba no fim (não deixa processo vivo).

Uso, na raiz da worktree da arte:  python3 tools/arte/visor/testar_servidor.py
Os pedidos vão crus por socket, para o cliente não "limpar" o "..".
"""

import os
import socket
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
HOST, PORT = "127.0.0.1", 8765

# (caminho, códigos aceitos). Recusa = 403 (ou 400 do próprio http.server para lixo).
CASOS = [
    ("/", {302}),
    ("/tools/arte/visor/index.html", {200, 404}),  # 404 enquanto o index.html não existe
    ("/tools/arte/visor/servir.py", {200}),
    ("/assets/previews/protagonista_v2/recortes.png", {200}),
    ("/.env", {403}),
    ("/%2eenv", {403}),
    ("/assets/../.env", {403}),
    ("/assets/%2e%2e/.env", {403}),
    ("/assets/%252e%252e/.env", {403}),
    ("/assets/..%2f.env", {403}),
    ("/assets/..%5c.env", {403}),
    ("/../.env", {403}),
    ("/tools/arte/visor/../../../.env", {403}),
    ("/tools/arte/visor/../godot_import.py", {403}),
    ("/tools/arte/godot_import.py", {403}),
    ("/tools/arte/visor/vendor/../../../../project.godot", {403}),
    ("/project.godot", {403}),
    ("/docs/GDD.md", {403}),
    ("/src/View/CameraRig.cs", {403}),
    ("/.git/config", {403}),
    ("/assets/", {403}),
    ("/assets", {403}),
    ("/assets/nao_existe.png", {404}),
    ("//etc/passwd", {403}),
    ("/assets//../../.env", {403}),
]


def pedir(caminho, host=f"{HOST}:{PORT}"):
    with socket.create_connection((HOST, PORT), timeout=5) as s:
        s.sendall(f"GET {caminho} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode("latin-1"))
        dados = b""
        while True:
            parte = s.recv(65536)
            if not parte:
                break
            dados += parte
    linha = dados.split(b"\r\n", 1)[0].decode("latin-1")
    return int(linha.split()[1]), dados


def main():
    with socket.socket() as s:
        if s.connect_ex((HOST, PORT)) == 0:
            print(f"A porta {PORT} já está em uso (o visor está rodando no terminal Visor?). Pare-o antes do teste.")
            return 2
    proc = subprocess.Popen([sys.executable, os.path.join(AQUI, "servir.py")],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    falhas = 0
    try:
        for _ in range(50):
            try:
                socket.create_connection((HOST, PORT), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        for caminho, ok in CASOS:
            codigo, dados = pedir(caminho)
            vazou = b"MESHY" in dados.upper() and "env" in caminho
            certo = codigo in ok and not vazou
            falhas += not certo
            print(f"{'ok   ' if certo else 'FALHA'} {codigo} {caminho}")
        codigo, _ = pedir("/assets/previews/protagonista_v2/recortes.png", host="evil.example:8765")
        falhas += codigo != 403
        print(f"{'ok   ' if codigo == 403 else 'FALHA'} {codigo} Host estranho recusado")
        # Só em 127.0.0.1: pela interface de rede externa não pode responder.
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as u:
                u.connect(("192.0.2.1", 9))  # UDP não envia nada; só escolhe a interface de saída
                externo = u.getsockname()[0]
        except OSError:
            externo = None
        if externo and not externo.startswith("127."):
            with socket.socket() as s:
                s.settimeout(1)
                aberto = s.connect_ex((externo, PORT)) == 0
            falhas += aberto
            print(f"{'FALHA' if aberto else 'ok   '} porta fechada em {externo}")
    finally:
        proc.terminate()
        proc.wait(timeout=5)
    print(f"servidor derrubado (código {proc.returncode}); {falhas} falha(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
