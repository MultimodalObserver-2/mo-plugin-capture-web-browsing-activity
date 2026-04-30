import asyncio
import json
import os
import threading
import time
from typing import Any, Callable
from mo.core import load_metadata_json
from mo.modules.capture import CaptureData, CapturePlugin
from mo.modules.communication.services.server_service import ServerService
from models import CSV_HEADERS
from server import WebActivityHTTPServer


@load_metadata_json("../..")
class WebBrowsingActivityCapturePlugin(CapturePlugin):
    def load(self) -> None:
        self.http_server: WebActivityHTTPServer | None = None
        self.session_path: str | None = None
        self.file_name: str | None = None
        self.output_dir: str | None = None
        self.output_files: dict[str, dict] = {}
        self.map: dict[str, str] = {}

    def unload(self) -> None:
        if self.http_server:
            self.http_server.stop()
            self.http_server = None

    def prepare(self, path: str, file_name: str) -> None:
        self.session_path = path
        self.file_name = file_name
        self.output_dir = os.path.join(path, file_name)
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_files = {}
        self.map = {}

    def start(self, start_ts: float, get_timestamp: Callable[[], float], on_data: Callable[[CaptureData], None]) -> None:
        host = self.settings.get_setting("server_host") or "localhost"
        port = int(self.settings.get_setting("server_port") or 3000)

        self.http_server = WebActivityHTTPServer(
            host=host,
            port=port,
            get_timestamp=get_timestamp,
            on_data=on_data,
        )
        self.http_server.start()
        self.register_with_communication_module()

    def pause(self, pause_ts: float) -> None:
        if self.http_server:
            self.http_server.pause()

    def resume(self, resume_ts: float) -> None:
        if self.http_server:
            self.http_server.resume()

    def stop(self, stop_ts: float) -> None:
        if self.http_server:
            self.http_server.stop()
            self.http_server = None
        self.close_output_files()
        self.write_map_file()

    def save(self, data: list[CaptureData], end_of_data: bool = False) -> None:
        export_csv = bool(self.settings.get_setting("export_to_csv") or False)
        stream_val = self.settings.get_setting("stream_to_clients")
        stream = stream_val if stream_val is not None else True

        for capture_data in data:
            event = capture_data.data
            if not isinstance(event, dict):
                continue
            event_type = event.get("event_type")
            if not event_type:
                continue
            if event_type not in self.output_files:
                self.open_files_for_type(event_type, export_csv)

            handles = self.output_files[event_type]
            jf = handles["json"]
            if not handles["json_first"]:
                jf.write(",\n")
            record = dict(event)
            record.pop("event_type", None)
            jf.write(json.dumps(record, ensure_ascii=False))
            handles["json_first"] = False

            cf = handles.get("csv")
            if cf:
                row = self.to_csv_row(event, event_type)
                cf.write(row + "\n")

            if stream:
                self.stream_event(event)

        if end_of_data:
            self.close_output_files()
            self.write_map_file()

    def get_file_extension(self) -> str:
        return "json"

    def get_output_descriptor(self) -> dict[str, Any] | None:
        return {
            "format": "web_activity_map",
            "event_types": list(CSV_HEADERS.keys()),
            "server_address": self.http_server.address if self.http_server else None,
        }

    @staticmethod
    def run_register(plugin_id: str, initial_config) -> None:
        asyncio.run(ServerService().add_active_capture_plugin(plugin_id, initial_config))

    def register_with_communication_module(self) -> None:
        plugin_id = self.metadata.plugin_id
        initial_config = self.get_output_descriptor()
        threading.Thread(
            target=WebBrowsingActivityCapturePlugin.run_register,
            args=(plugin_id, initial_config),
            name="web-activity-comm-register",
            daemon=True,
        ).start()

    def stream_event(self, event: dict) -> None:
        ServerService().send_capture_data(event)

    def open_files_for_type(self, event_type: str, export_csv: bool) -> None:
        base = os.path.join(self.output_dir, event_type)
        json_path = base + ".json"
        jf = open(json_path, "w", encoding="utf-8")
        jf.write("[")

        handles = {
            "json": jf,
            "json_path": json_path,
            "json_first": True,
            "csv": None,
        }

        if export_csv:
            csv_path = base + ".csv"
            cf = open(csv_path, "w", encoding="utf-8", newline="")
            headers = CSV_HEADERS.get(event_type, [])
            cf.write(",".join(headers) + "\n")
            handles["csv"] = cf

        self.output_files[event_type] = handles
        self.map[event_type] = os.path.abspath(json_path)

    def close_output_files(self) -> None:
        for handles in self.output_files.values():
            jf = handles["json"]
            jf.write("]")
            jf.flush()
            jf.close()
            cf = handles.get("csv")
            if cf:
                cf.flush()
                cf.close()
        self.output_files.clear()

    def write_map_file(self) -> None:
        if not self.map or not self.session_path or not self.file_name:
            return
        map_path = os.path.join(
            self.session_path, f"{self.file_name}.json"
        )
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(self.map, f, indent=2, ensure_ascii=False)

    @staticmethod
    def to_csv_row(event: dict, event_type: str, sep: str = ",") -> str:
        headers = CSV_HEADERS.get(event_type, [])
        values = []
        for h in headers:
            v = event.get(h, "")
            s = str(v) if v is not None else ""
            if sep in s or '"' in s or "\n" in s:
                s = '"' + s.replace('"', '""') + '"'
            values.append(s)
        return sep.join(values)

    @staticmethod
    def elapsed_since(ts: float) -> float:
        return time.monotonic() - ts
