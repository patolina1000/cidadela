"""Servidor local do visor de arte (só biblioteca padrão).

Escuta só em 127.0.0.1:8765 e entrega só tools/arte/visor/ e assets/. Recusa qualquer outro caminho,
a raiz do repositório, arquivos ocultos (.env, .git...) e "..", mesmo codificado (%2e%2e) ou por link
simbólico. Sem listagem de pastas.

Uso, na raiz da worktree da arte:  python3 tools/arte/visor/servir.py
Abre em http://127.0.0.1:8765/  (redireciona para o visor).
"""

import http.server
import os
import posixpath
import sys
from urllib.parse import unquote, urlsplit

HOST = "127.0.0.1"
PORT = 8765
ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
ALLOWED = ("tools/arte/visor/", "assets/")
HOSTS_OK = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}


def resolve(url_path):
    """Caminho da URL -> arquivo no disco, ou None se for recusado."""
    path = urlsplit(url_path).path
    # Decodifica duas vezes para pegar %252e%252e; qualquer barra invertida ou NUL é recusada.
    raw = unquote(unquote(path))
    if "\\" in raw or "\x00" in raw:
        return None
    parts = [p for p in raw.split("/") if p]
    if not parts or any(p == ".." or p.startswith(".") for p in parts):
        return None
    rel = "/".join(parts)
    if raw.endswith("/"):
        rel += "/"
    if posixpath.normpath(rel).startswith("..") or not rel.startswith(ALLOWED):
        return None
    full = os.path.realpath(os.path.join(ROOT, *parts))
    # O real (sem links simbólicos) também precisa cair numa das pastas permitidas.
    for prefix in ALLOWED:
        base = os.path.realpath(os.path.join(ROOT, prefix))
        if full == base or full.startswith(base + os.sep):
            return full
    return None


class Handler(http.server.SimpleHTTPRequestHandler):
    server_version = "VisorArte/1"
    sys_version = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def _host_ok(self):
        # Contra "DNS rebinding": só aceita quem chama pelo endereço local.
        return self.headers.get("Host", "") in HOSTS_OK

    def do_GET(self):
        self._serve(head=False)

    def do_HEAD(self):
        self._serve(head=True)

    def _serve(self, head):
        if not self._host_ok():
            self.send_error(403, "Host recusado")
            return
        if urlsplit(self.path).path in ("/", "/tools/arte/visor", "/tools/arte/visor/"):
            self.send_response(302)
            self.send_header("Location", "/tools/arte/visor/index.html")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        full = resolve(self.path)
        if full is None:
            self.send_error(403, "Caminho recusado")
            return
        if os.path.isdir(full):
            self.send_error(403, "Sem listagem")
            return
        if not os.path.isfile(full):
            self.send_error(404, "Não encontrado")
            return
        try:
            f = open(full, "rb")
        except OSError:
            self.send_error(404, "Não encontrado")
            return
        with f:
            size = os.fstat(f.fileno()).st_size
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(full))
            self.send_header("Content-Length", str(size))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if not head:
                self.copyfile(f, self.wfile)

    def list_directory(self, path):  # nunca lista pastas
        self.send_error(403, "Sem listagem")
        return None


Handler.extensions_map = dict(Handler.extensions_map)
Handler.extensions_map.update({
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".json": "application/json",
    ".glb": "model/gltf-binary",
    ".gif": "image/gif",
})


def main():
    httpd = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Visor em http://{HOST}:{PORT}/  (raiz {ROOT}; Ctrl+C para parar)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    sys.exit(main())
