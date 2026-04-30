import json
import os
import shutil
import socket
import sys
import tempfile
import time
import types
import unittest
import urllib.error
import urllib.request
from unittest.mock import MagicMock

comm_mod = types.ModuleType("mo.modules.communication")
comm_svc_mod = types.ModuleType("mo.modules.communication.services")
comm_ss_mod = types.ModuleType("mo.modules.communication.services.server_service")


class StubServerService:
    def __new__(cls, *args, **kwargs):
        return object.__new__(cls)

    def send_capture_data(self, data) -> None:
        pass

    async def add_active_capture_plugin(self, plugin_id, config=None) -> None:
        pass


comm_ss_mod.ServerService = StubServerService
sys.modules.setdefault("mo.modules.communication", comm_mod)
sys.modules.setdefault("mo.modules.communication.services", comm_svc_mod)
sys.modules.setdefault("mo.modules.communication.services.server_service", comm_ss_mod)

from mo.modules.capture import CaptureData
from web_browsing_activity_recorder.main import WebBrowsingActivityCapturePlugin
from web_browsing_activity_recorder.models import (
    CSV_HEADERS,
    Keystroke,
    MouseClick,
    MouseMove,
    MouseUp,
    SearchAction,
    TabAction,
    get_int,
    parse_event,
)
from web_browsing_activity_recorder.server import MOUNTED, RUNNING, WebActivityHTTPServer


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def get_response(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}


def post_request(url: str, body: dict | None = None) -> tuple[int, str]:
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def make_plugin(settings_map: dict | None = None) -> WebBrowsingActivityCapturePlugin:
    plugin = WebBrowsingActivityCapturePlugin()
    plugin.settings = MagicMock()
    plugin.settings.get_setting.side_effect = lambda k: (settings_map or {}).get(k)
    plugin.load()
    return plugin


class TestWebBrowsingActivity(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.port = free_port()
        self.plugin = make_plugin({
            "server_host": "localhost",
            "server_port": self.port,
            "export_to_csv": False,
            "stream_to_clients": False,
        })

    def tearDown(self):
        self.plugin.unload()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def start_test_server(self, received=None):
        port = free_port()
        on_data = received.append if received is not None else lambda d: None
        server = WebActivityHTTPServer(host="localhost", port=port,get_timestamp=lambda: 1.0, on_data=on_data, )
        server.start()
        time.sleep(0.1)
        return server

    def prepare_session(self, name="sess"):
        self.plugin.prepare(self.tmp, name)
        return os.path.join(self.tmp, name)

    def keystroke_data(self, ts: float = 1.0) -> CaptureData:
        ev = parse_event("/keystrokes", {"browser": "Chrome", "keyValue": "a"}, ts)
        return CaptureData(timestamp=ts, data=ev)

    def tab_data(self, ts: float = 2.0) -> CaptureData:
        ev = parse_event("/tabs", {"tabUrl": "https://x.com", "actionType": "open"}, ts)
        return CaptureData(timestamp=ts, data=ev)

    def test_keystrokes(self):
        ev = parse_event("/keystrokes", {"browser": "Chrome", "pageUrl": "https://x.com",
                                         "pageTitle": "X", "keyValue": "a"}, 123.45)
        self.assertIsNotNone(ev)
        self.assertEqual(ev["event_type"], "keystrokes")
        self.assertEqual(ev["browser"], "Chrome")
        self.assertEqual(ev["keyValue"], "a")
        self.assertEqual(ev["captureTimestamp"], 123.45)

    def test_mouse_clicks(self):
        ev = parse_event("/mouseClicks", {"browser": "Firefox", "pageUrl": "u",
                                          "xPage": 10, "yPage": 20, "button": 1}, 123.45)
        self.assertEqual(ev["event_type"], "mouseClicks")
        self.assertEqual(ev["xPage"], 10)
        self.assertEqual(ev["button"], 1)

    def test_mouse_moves(self):
        ev = parse_event("/mouseMoves", {"xMovement": 3, "yMovement": -2}, 123.45)
        self.assertEqual(ev["event_type"], "mouseMoves")
        self.assertEqual(ev["xMovement"], 3)
        self.assertEqual(ev["yMovement"], -2)

    def test_mouse_ups(self):
        ev = parse_event("/mouseUps", {"selectedText": "hello"}, 123.45)
        self.assertEqual(ev["event_type"], "mouseUps")
        self.assertEqual(ev["selectedText"], "hello")

    def test_searchs(self):
        ev = parse_event("/searchs", {"search": "pytest"}, 123.45)
        self.assertEqual(ev["event_type"], "searchs")
        self.assertEqual(ev["search"], "pytest")

    def test_tabs(self):
        ev = parse_event("/tabs", {"tabUrl": "https://x.com", "actionType": "open",
                                   "tabIndex": 0, "tabId": 1, "windowId": 2}, 123.45)
        self.assertEqual(ev["event_type"], "tabs")
        self.assertEqual(ev["actionType"], "open")
        self.assertEqual(ev["tabId"], 1)

    def test_unknown_path_none(self):
        self.assertIsNone(parse_event("/unknown", {}, 123.45))

    def test_missing_fields_defaults(self):
        ev = parse_event("/keystrokes", {}, 123.45)
        self.assertEqual(ev["browser"], "")
        self.assertEqual(ev["keyValue"], "")

    def test_keystroke_dict_event_type(self):
        d = Keystroke(browser="B", keyValue="x").to_dict()
        self.assertEqual(d["event_type"], "keystrokes")
        self.assertNotIn("event_type", Keystroke.__dataclass_fields__)

    def test_mouse_up_csv_comma_quoted(self):
        mu = MouseUp(selectedText="hello, world")
        row = mu.to_csv_row()
        self.assertIn('"hello, world"', row)

    def test_csv_headers_event_types(self):
        expected = {"keystrokes", "mouseClicks", "mouseMoves", "mouseUps", "searchs", "tabs"}
        self.assertEqual(set(CSV_HEADERS.keys()), expected)

    def test_tab_action_dict(self):
        d = TabAction(tabUrl="https://x.com", actionType="close").to_dict()
        self.assertEqual(d["event_type"], "tabs")
        self.assertEqual(d["tabUrl"], "https://x.com")

    def test_search_action_csv_row(self):
        row = SearchAction(browser="B", search="Python").to_csv_row()
        self.assertIn("Python", row)

    def test_get_int_invalid_zero(self):
        self.assertEqual(get_int({"x": "abc"}, "x"), 0)

    def test_get_int_none_zero(self):
        self.assertEqual(get_int({"x": None}, "x"), 0)

    def test_keystroke_csv_row(self):
        k = Keystroke(browser="B", pageUrl="u", pageTitle="t", keyValue="a", captureTimestamp=1.0)
        row = k.to_csv_row()
        self.assertIn("a", row)
        self.assertIn("B", row)

    def test_mouse_click_csv_row(self):
        mc = MouseClick(browser="B", xPage=10, yPage=20, button=1, captureTimestamp=2.0)
        row = mc.to_csv_row()
        self.assertIn("10", row)
        self.assertIn("1", row)

    def test_mouse_move_csv_row(self):
        mm = MouseMove(xMovement=5, yMovement=-3, captureTimestamp=3.0)
        row = mm.to_csv_row()
        self.assertIn("5", row)
        self.assertIn("-3", row)

    def test_tab_csv_row(self):
        ta = TabAction(browser="Firefox", actionType="open", tabIndex=1, tabId=2, windowId=3)
        row = ta.to_csv_row()
        self.assertIn("Firefox", row)
        self.assertIn("open", row)

    def test_server_address(self):
        port = free_port()
        server = WebActivityHTTPServer(host="localhost", port=port,
                                       get_timestamp=lambda: 1.0, on_data=lambda d: None)
        self.assertEqual(server.address, f"http://localhost:{port}")

    def test_server_initial_state_mounted(self):
        server = self.start_test_server()
        try:
            self.assertEqual(server.state, MOUNTED)
        finally:
            server.stop()
            time.sleep(0.1)

    def test_server_status_mounted(self):
        server = self.start_test_server()
        try:
            code, body = get_response(f"{server.address}/status")
            self.assertEqual(code, 200)
            self.assertEqual(body["status"], MOUNTED)
        finally:
            server.stop()
            time.sleep(0.1)

    def test_server_post_start_running(self):
        server = self.start_test_server()
        try:
            code, _ = post_request(f"{server.address}/start")
            self.assertEqual(code, 200)
            self.assertEqual(server.state, RUNNING)
        finally:
            server.stop()
            time.sleep(0.1)

    def test_server_post_stop_mounted(self):
        server = self.start_test_server()
        try:
            post_request(f"{server.address}/start")
            code, _ = post_request(f"{server.address}/stop")
            self.assertEqual(code, 200)
            self.assertEqual(server.state, MOUNTED)
        finally:
            server.stop()
            time.sleep(0.1)

    def test_server_event_pre_start_503(self):
        received = []
        server = self.start_test_server(received)
        try:
            code, _ = post_request(f"{server.address}/keystrokes", {"keyValue": "a"})
            self.assertEqual(code, 503)
            self.assertEqual(len(received), 0)
        finally:
            server.stop()
            time.sleep(0.1)

    def test_server_event_calls_on_data(self):
        received = []
        server = self.start_test_server(received)
        try:
            post_request(f"{server.address}/start")
            code, _ = post_request(f"{server.address}/keystrokes",
                                   {"browser": "B", "pageUrl": "u", "keyValue": "z"})
            self.assertEqual(code, 200)
            self.assertEqual(len(received), 1)
            self.assertEqual(received[0].data["keyValue"], "z")
        finally:
            server.stop()
            time.sleep(0.1)

    def test_server_unknown_path_no_data(self):
        received = []
        server = self.start_test_server(received)
        try:
            post_request(f"{server.address}/start")
            code, _ = post_request(f"{server.address}/notAnEvent", {})
            self.assertEqual(code, 200)
            self.assertEqual(len(received), 0)
        finally:
            server.stop()
            time.sleep(0.1)

    def test_server_pause_drops_events(self):
        received = []
        server = self.start_test_server(received)
        try:
            post_request(f"{server.address}/start")
            server.pause()
            code, _ = post_request(f"{server.address}/keystrokes", {"keyValue": "x"})
            self.assertEqual(code, 503)
            self.assertEqual(len(received), 0)
        finally:
            server.stop()
            time.sleep(0.1)

    def test_server_resume_accepts_events(self):
        received = []
        server = self.start_test_server(received)
        try:
            post_request(f"{server.address}/start")
            server.pause()
            server.resume()
            code, _ = post_request(f"{server.address}/keystrokes", {"keyValue": "y"})
            self.assertEqual(code, 200)
            self.assertEqual(len(received), 1)
        finally:
            server.stop()
            time.sleep(0.1)

    def test_server_all_event_paths(self):
        received = []
        server = self.start_test_server(received)
        try:
            post_request(f"{server.address}/start")
            paths = [
                ("/keystrokes", {"keyValue": "k"}),
                ("/mouseClicks", {"xPage": 1, "yPage": 2}),
                ("/mouseMoves", {"xMovement": 1, "yMovement": 0}),
                ("/mouseUps", {"selectedText": "hi"}),
                ("/searchs", {"search": "q"}),
                ("/tabs", {"tabUrl": "u", "actionType": "open"}),
            ]
            for path, body in paths:
                code, _ = post_request(f"{server.address}{path}", body)
                self.assertEqual(code, 200, f"Falló {path}")
            self.assertEqual(len(received), len(paths))
        finally:
            server.stop()
            time.sleep(0.1)

    def test_server_options_200(self):
        server = self.start_test_server()
        try:
            req = urllib.request.Request(f"{server.address}/keystrokes", method="OPTIONS")
            try:
                with urllib.request.urlopen(req, timeout=3) as r:
                    self.assertEqual(r.status, 200)
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 200)
        finally:
            server.stop()
            time.sleep(0.1)

    def test_server_unknown_path_404(self):
        server = self.start_test_server()
        try:
            try:
                urllib.request.urlopen(f"{server.address}/notfound", timeout=3)
                self.fail("Expected 404")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 404)
        finally:
            server.stop()
            time.sleep(0.1)

    def test_server_post_invalid_json(self):
        server = self.start_test_server()
        try:
            req = urllib.request.Request(
                f"{server.address}/start",
                data=b"not-json",
                headers={"Content-Type": "application/json", "Content-Length": "8"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=3) as r:
                    self.assertIn(r.status, [200, 503])
            except urllib.error.HTTPError as e:
                self.assertIn(e.code, [200, 503])
        finally:
            server.stop()
            time.sleep(0.1)

    def test_load_initial_state(self):
        self.assertIsNone(self.plugin.http_server)
        self.assertIsNone(self.plugin.session_path)
        self.assertEqual(self.plugin.output_files, {})

    def test_prepare_output_dir(self):
        self.plugin.prepare(self.tmp, "sess")
        self.assertTrue(os.path.isdir(os.path.join(self.tmp, "sess")))

    def test_start_http_server(self):
        self.plugin.prepare(self.tmp, "sess")
        self.plugin.start(0.0, time.monotonic, lambda d: None)
        time.sleep(0.1)
        self.assertIsNotNone(self.plugin.http_server)
        code, _ = get_response(f"http://localhost:{self.port}/status")
        self.assertEqual(code, 200)

    def test_stop_server(self):
        self.plugin.prepare(self.tmp, "sess")
        self.plugin.start(0.0, time.monotonic, lambda d: None)
        time.sleep(0.1)
        self.plugin.stop(1.0)
        time.sleep(0.2)
        self.assertIsNone(self.plugin.http_server)

    def test_pause_resume(self):
        received = []
        self.plugin.prepare(self.tmp, "sess")
        self.plugin.start(0.0, time.monotonic, received.append)
        time.sleep(0.1)
        post_request(f"http://localhost:{self.port}/start")
        self.plugin.pause(0.5)
        code, _ = post_request(f"http://localhost:{self.port}/keystrokes", {"keyValue": "x"})
        self.assertEqual(code, 503)
        self.plugin.resume(1.0)
        code, _ = post_request(f"http://localhost:{self.port}/keystrokes", {"keyValue": "y"})
        self.assertEqual(code, 200)

    def test_file_extension(self):
        self.assertEqual(self.plugin.get_file_extension(), "json")

    def test_output_descriptor_no_server(self):
        desc = self.plugin.get_output_descriptor()
        self.assertEqual(desc["format"], "web_activity_map")
        self.assertIsNone(desc["server_address"])

    def test_output_descriptor_server(self):
        self.plugin.prepare(self.tmp, "sess")
        self.plugin.start(0.0, time.monotonic, lambda d: None)
        time.sleep(0.1)
        desc = self.plugin.get_output_descriptor()
        self.assertIn(str(self.port), desc["server_address"])
        self.plugin.stop(1.0)

    def test_unload_server(self):
        self.plugin.prepare(self.tmp, "sess")
        self.plugin.start(0.0, time.monotonic, lambda d: None)
        time.sleep(0.1)
        self.plugin.unload()
        self.assertIsNone(self.plugin.http_server)

    def test_save_json(self):
        out_dir = self.prepare_session()
        self.plugin.save([self.keystroke_data()], end_of_data=True)
        json_path = os.path.join(out_dir, "keystrokes.json")
        self.assertTrue(os.path.exists(json_path))
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["keyValue"], "a")

    def test_save_multiple_types(self):
        out_dir = self.prepare_session()
        self.plugin.save([self.keystroke_data(1.0), self.tab_data(2.0)], end_of_data=True)
        self.assertTrue(os.path.exists(os.path.join(out_dir, "keystrokes.json")))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "tabs.json")))

    def test_save_multiple_same_type(self):
        out_dir = self.prepare_session()
        self.plugin.save([self.keystroke_data(float(i)) for i in range(4)], end_of_data=True)
        with open(os.path.join(out_dir, "keystrokes.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 4)

    def test_save_csv(self):
        self.plugin.settings.get_setting.side_effect = lambda k: True if k == "export_to_csv" else None
        out_dir = self.prepare_session()
        self.plugin.save([self.keystroke_data()], end_of_data=True)
        csv_path = os.path.join(out_dir, "keystrokes.csv")
        self.assertTrue(os.path.exists(csv_path))
        with open(csv_path, encoding="utf-8") as f:
            lines = f.readlines()
        self.assertGreaterEqual(len(lines), 2)
        self.assertIn("browser", lines[0])

    def test_save_non_dict(self):
        out_dir = self.prepare_session()
        self.plugin.save([CaptureData(timestamp=0.0, data="no soy un dict")], end_of_data=True)
        self.assertEqual(os.listdir(out_dir), [])

    def test_end_data_map_file(self):
        out_dir = self.prepare_session()
        self.plugin.save([self.keystroke_data()], end_of_data=True)
        map_path = os.path.join(self.tmp, "sess.json")
        self.assertTrue(os.path.exists(map_path))
        with open(map_path, encoding="utf-8") as f:
            m = json.load(f)
        self.assertIn("keystrokes", m)

    def test_end_data_closes_files(self):
        self.prepare_session()
        self.plugin.save([self.keystroke_data()], end_of_data=True)
        self.assertEqual(self.plugin.output_files, {})

    def test_json_valid_end_data(self):
        out_dir = self.prepare_session()
        self.plugin.save([self.keystroke_data(float(i)) for i in range(5)], end_of_data=True)
        with open(os.path.join(out_dir, "keystrokes.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 5)

    def test_save_split_batches(self):
        out_dir = self.prepare_session()
        for i in range(3):
            self.plugin.save([self.keystroke_data(float(i))])
        self.plugin.save([], end_of_data=True)
        with open(os.path.join(out_dir, "keystrokes.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 3)

    def test_save_no_event_type(self):
        out_dir = self.prepare_session("extra_sess")
        self.plugin.save([CaptureData(timestamp=1.0, data={"browser": "X"})], end_of_data=True)
        self.assertEqual(os.listdir(out_dir), [])

    def test_csv_row_comma_quoted(self):
        event = {"event_type": "mouseUps", "browser": "B", "pageUrl": "u",
                 "pageTitle": "t", "selectedText": "hello, world", "captureTimestamp": 1.0}
        row = WebBrowsingActivityCapturePlugin.to_csv_row(event, "mouseUps")
        self.assertIn('"hello, world"', row)

    def test_elapsed_since(self):
        ts = time.monotonic()
        time.sleep(0.05)
        elapsed = WebBrowsingActivityCapturePlugin.elapsed_since(ts)
        self.assertGreater(elapsed, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
