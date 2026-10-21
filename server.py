"""Python 3.12: two-route large-file transfer site for Linux."""

import hmac
import json
import os
import re
import threading
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHUNK_SIZE = 1024 * 1024
MAX_BYTES = 2 * 1024**3 - 1
UPLOAD_LOCK = threading.Lock()


def data_dir():
    path = Path(os.getenv("DATA_DIR", str(ROOT / "data"))).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def respond(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/upload")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/upload":
            body = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/download":
            with UPLOAD_LOCK:
                directory = data_dir()
                try:
                    meta = json.loads((directory / "latest.json").read_text())
                    filename = meta["name"]
                    file_id = meta["id"]
                    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", filename) or not re.fullmatch(r"[0-9a-f]{32}", file_id):
                        raise ValueError("Invalid metadata")
                    source = (directory / f"{file_id}.bin").open("rb")
                except FileNotFoundError:
                    self.respond(404, {"error": "Ainda não há ficheiro para descarregar."})
                    return
                except (OSError, ValueError, KeyError):
                    self.respond(500, {"error": "O ficheiro guardado não está disponível."})
                    return
            with source:
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Content-Length", str(os.fstat(source.fileno()).st_size))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    while block := source.read(CHUNK_SIZE):
                        self.wfile.write(block)
                except (BrokenPipeError, ConnectionResetError):
                    pass
            return
        self.respond(404, {"error": "Página não encontrada."})

    def do_POST(self):
        if urllib.parse.urlsplit(self.path).path != "/upload":
            self.close_connection = True
            self.respond(404, {"error": "Rota não encontrada."})
            return
        secret = os.getenv("UPLOAD_KEY", "")
        if not secret:
            self.close_connection = True
            self.respond(503, {"error": "Configura UPLOAD_KEY no servidor."})
            return
        if not hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {secret}"):
            self.close_connection = True
            self.respond(401, {"error": "Chave de upload inválida."})
            return
        name = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("name", [""])[0]
        if not name or len(name.encode()) > 255 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) or name in (".", ".."):
            self.close_connection = True
            self.respond(400, {"error": "Nome inválido. Usa letras, números, ponto, hífen ou underscore."})
            return
        length = self.headers.get("Content-Length", "")
        if not length.isdecimal():
            self.close_connection = True
            self.respond(411, {"error": "É necessário indicar o tamanho do ficheiro."})
            return
        size = int(length)
        if not 0 < size <= MAX_BYTES:
            self.close_connection = True
            self.respond(413, {"error": "O ficheiro tem de ter menos de 2 GiB."})
            return

        directory = data_dir()
        file_id = uuid.uuid4().hex
        temporary = directory / f"{file_id}.part"
        final = directory / f"{file_id}.bin"
        try:
            remaining = size
            with temporary.open("wb") as output:
                while remaining:
                    block = self.rfile.read(min(CHUNK_SIZE, remaining))
                    if not block:
                        raise ConnectionError("Incomplete request")
                    output.write(block)
                    remaining -= len(block)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, final)
            with UPLOAD_LOCK:
                pointer = directory / "latest.json"
                previous = None
                if pointer.exists():
                    try:
                        previous = json.loads(pointer.read_text()).get("id")
                    except (OSError, ValueError):
                        pass
                pending = directory / f"{file_id}.json.part"
                pending.write_text(json.dumps({"id": file_id, "name": name}))
                os.replace(pending, pointer)
                if previous and re.fullmatch(r"[0-9a-f]{32}", previous):
                    try:
                        (directory / f"{previous}.bin").unlink(missing_ok=True)
                    except OSError:
                        pass
            self.respond(201, {"url": "/download"})
        except (OSError, ConnectionError):
            self.close_connection = True
            self.respond(500, {"error": "Upload interrompido. Tenta novamente."})
        finally:
            temporary.unlink(missing_ok=True)


def main():
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Listening on port {port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
