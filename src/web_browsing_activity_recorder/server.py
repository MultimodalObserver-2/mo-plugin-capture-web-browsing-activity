import json
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Callable

from models import parse_event

MOUNTED = "mounted"
RUNNING = "running"
PAUSED  = "paused"
STOPPED = "stopped"


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class ActivityHandler(BaseHTTPRequestHandler):
    server_ref: "WebActivityHTTPServer | None" = None

    def log_message(self, fmt, *args):
        pass

    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.cors()
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path in ("/status", ""):
            body = json.dumps({
                "status": self.server_ref._state,
                "host": self.server_ref._host,
                "port": self.server_ref._port,
            }).encode()
            self.send_response(200)
            self.cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.cors()
            self.end_headers()

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}

        ts = self.server_ref._get_timestamp() if self.server_ref._get_timestamp else time.time()

        if path == "/start":
            self.server_ref._state = RUNNING
            self.respond(200, "Capture started")
            return

        if path == "/stop":
            self.server_ref._state = MOUNTED
            self.respond(200, "Capture stopped")
            return

        if self.server_ref._state == PAUSED:
            self.respond(503, "Capture paused")
            return

        if self.server_ref._state != RUNNING:
            self.respond(503, "Capture not running")
            return

        event = parse_event(path, payload, ts)
        if event is not None and self.server_ref._on_data is not None:
            from mo.modules.capture import CaptureData
            self.server_ref._on_data(CaptureData(timestamp=ts, data=event))

        self.respond(200, "OK")

    def respond(self, code: int, message: str):
        body = message.encode("utf-8")
        self.send_response(code)
        self.cors()
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class WebActivityHTTPServer:

    def __init__(
        self,
        host: str,
        port: int,
        get_timestamp: Callable[[], float] | None,
        on_data: Callable | None,
    ):
        self._host = host
        self._port = port
        self._get_timestamp = get_timestamp
        self._on_data = on_data
        self._state: str = MOUNTED
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        ActivityHandler.server_ref = self
        self._server = ThreadingHTTPServer((self._host, self._port), ActivityHandler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="web-activity-http-server",
            daemon=True,
        )
        self._thread.start()

    def pause(self) -> None:
        self._state = PAUSED

    def resume(self) -> None:
        if self._state == PAUSED:
            self._state = RUNNING

    def stop(self) -> None:
        self._state = STOPPED
        if self._server:
            threading.Thread(target=self._server.shutdown, daemon=True).start()
            self._server = None

    @property
    def address(self) -> str:
        return f"http://{self._host}:{self._port}"

    @property
    def state(self) -> str:
        return self._state
