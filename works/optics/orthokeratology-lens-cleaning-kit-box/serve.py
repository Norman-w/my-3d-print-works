#!/usr/bin/env python3
"""LAN preview server and optional Bambu Lab LAN bridge.

The preview is intentionally dependency-free.  The optional printer bridge
uses the LAN-only MQTT/FTPS endpoints and only accepts a pre-sliced
`.gcode.3mf`; an STL still needs a printer profile and a slicer first.
Credentials are read from the request or an ignored local config file and are
never returned by the API or written by this server.
"""

from __future__ import annotations

import argparse
import ftplib
import hashlib
import ipaddress
import json
import mimetypes
import os
import re
import socket
import ssl
import struct
import subprocess
import time
import uuid
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


PROJECT_ROOT = Path(__file__).resolve().parent
WEB_ROOT = PROJECT_ROOT / "web"
STL_ROOT = PROJECT_ROOT / "output" / "3d-print"
PREVIEW_ROOT = PROJECT_ROOT / "output" / "previews"
JOB_ROOT = PROJECT_ROOT / "output" / "print-jobs"
LOCAL_CONFIG = PROJECT_ROOT / "bambu.local.json"

MAX_REQUEST_BYTES = 160 * 1024 * 1024
PRINTER_PORTS = {"mqtt": 8883, "ftps": 990}

def read_dimensions() -> dict[str, float]:
    """Read literal dimensions from the authoritative CAD source."""
    source = (PROJECT_ROOT / "orthokeratology_lens_cleaning_kit_box.scad").read_text()
    names = ("inner_length", "inner_width", "inner_height_total", "wall", "base_floor", "front_service", "rear_service", "mechanism_keepout", "axis_inset")
    values = {}
    for name in names:
        match = re.search(rf"^{name}\s*=\s*([0-9.]+)\s*;", source, re.MULTILINE)
        if not match:
            raise ValueError(f"CAD dimension missing: {name}")
        values[name] = float(match.group(1))
    return values


CAD_DIMENSIONS = read_dimensions()
MODEL_INFO = {
    "revision": "H",
    "wall": CAD_DIMENSIONS["wall"],
    "floor": CAD_DIMENSIONS["base_floor"],
    "seal": "none",
    "hingePivot": [0, CAD_DIMENSIONS["inner_width"] + 2 * CAD_DIMENSIONS["wall"] + CAD_DIMENSIONS["front_service"] + CAD_DIMENSIONS["rear_service"] - CAD_DIMENSIONS["axis_inset"], CAD_DIMENSIONS["base_floor"] + CAD_DIMENSIONS["inner_height_total"] / 2],
    "innerType": "clear_rectangular_cavity",
    "printPose": "90 degree opening, both shells inclined 45 degrees",
    "clearInner": {"length": CAD_DIMENSIONS["inner_length"], "width": CAD_DIMENSIONS["inner_width"] - CAD_DIMENSIONS["mechanism_keepout"], "height": CAD_DIMENSIONS["inner_height_total"]},
    "inner": {"length": CAD_DIMENSIONS["inner_length"], "width": CAD_DIMENSIONS["inner_width"], "height": CAD_DIMENSIONS["inner_height_total"]},
    "halfClearHeight": CAD_DIMENSIONS["inner_height_total"] / 2,
    "outer": {"length": CAD_DIMENSIONS["inner_length"] + 2 * CAD_DIMENSIONS["wall"], "width": CAD_DIMENSIONS["inner_width"] + 2 * CAD_DIMENSIONS["wall"] + CAD_DIMENSIONS["front_service"] + CAD_DIMENSIONS["rear_service"], "height": CAD_DIMENSIONS["inner_height_total"] + 2 * CAD_DIMENSIONS["base_floor"]},
    "process": "FDM / Bambu Lab X1C / 0.4 mm nozzle",
    "material": "Unfilled PETG prototype",
    "printAsset": "orthokeratology_lens_cleaning_kit_box_print_in_place_open.stl",
    "closedAsset": "orthokeratology_lens_cleaning_kit_box_closed_preview.stl",
    "baseAsset": "orthokeratology_lens_cleaning_kit_box_base.stl",
    "lidAsset": "orthokeratology_lens_cleaning_kit_box_lid.stl",
}


def load_local_config() -> dict[str, Any]:
    if not LOCAL_CONFIG.is_file():
        return {}
    try:
        value = json.loads(LOCAL_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def first_value(fields: dict[str, str], config: dict[str, Any], *names: str) -> str:
    for name in names:
        value = fields.get(name, "").strip()
        if value:
            return value
        configured = config.get(name, "")
        if isinstance(configured, str) and configured.strip():
            return configured.strip()
    return ""


def validate_printer_ip(raw: str) -> str:
    value = raw.strip()
    try:
        parsed = ipaddress.ip_address(value)
    except ValueError as exc:
        raise ValueError("打印机 IP 必须是局域网 IPv4/IPv6 地址。") from exc
    if parsed.is_unspecified or parsed.is_multicast:
        raise ValueError("打印机 IP 不能是未指定或组播地址。")
    return value


def safe_asset(root: Path, name: str) -> Path:
    candidate = (root / unquote(name)).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("非法资源路径。")
    if not candidate.is_file():
        raise FileNotFoundError(name)
    return candidate


def read_request_body(handler: BaseHTTPRequestHandler) -> bytes:
    try:
        content_length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise ValueError("Content-Length 无效。") from exc
    if content_length <= 0:
        raise ValueError("请求体为空。")
    if content_length > MAX_REQUEST_BYTES:
        raise ValueError("请求体超过 160 MB 限制。")
    return handler.rfile.read(content_length)


def parse_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    body = read_request_body(handler)
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("请求 JSON 无效。") from exc
    if not isinstance(value, dict):
        raise ValueError("请求 JSON 必须是对象。")
    return value


def parse_multipart(body: bytes, content_type: str) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
    header = (
        f"Content-Type: {content_type}\r\n"
        "MIME-Version: 1.0\r\n"
        "\r\n"
    ).encode("utf-8")
    message = BytesParser(policy=policy.default).parsebytes(header + body)
    if not message.is_multipart():
        raise ValueError("需要 multipart/form-data 请求。")

    fields: dict[str, str] = {}
    files: dict[str, tuple[str, bytes]] = {}
    for part in message.iter_parts():
        disposition = part.get("Content-Disposition", "")
        field_name = part.get_param("name", header="content-disposition")
        if not field_name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename:
            files[field_name] = (filename, payload)
        else:
            charset = part.get_content_charset() or "utf-8"
            fields[field_name] = payload.decode(charset, errors="replace")
    return fields, files


def port_probe(host: str, port: int, timeout: float = 2.5) -> dict[str, Any]:
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {
                "reachable": True,
                "latencyMs": round((time.monotonic() - started) * 1000, 1),
            }
    except OSError as exc:
        return {
            "reachable": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


class ImplicitFTP_TLS(ftplib.FTP_TLS):
    """Small implicit-TLS FTPS client for the printer's port 990."""

    def connect(
        self,
        host: str = "",
        port: int = 0,
        timeout: float = -999,
        source_address: tuple[str, int] | None = None,
    ) -> str:
        if host:
            self.host = host
        if port:
            self.port = port
        if timeout != -999:
            self.timeout = timeout
        self.sock = socket.create_connection(
            (self.host, self.port), self.timeout, source_address=source_address
        )
        self.af = self.sock.family
        self.sock = self.context.wrap_socket(self.sock, server_hostname=self.host)
        self.file = self.sock.makefile("r", encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome


def implicit_ftps_login(host: str, access_code: str) -> ImplicitFTP_TLS:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    client = ImplicitFTP_TLS(context=context, timeout=4.0)
    client.connect(host, PRINTER_PORTS["ftps"])
    client.login("bblp", access_code)
    client.prot_p()
    return client


def mqtt_remaining_length(value: int) -> bytes:
    if value < 0:
        raise ValueError("MQTT remaining length cannot be negative")
    encoded = bytearray()
    while True:
        digit = value % 128
        value //= 128
        if value:
            digit |= 0x80
        encoded.append(digit)
        if not value:
            return bytes(encoded)


def mqtt_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return struct.pack(">H", len(encoded)) + encoded


class BambuMQTT:
    def __init__(self, host: str, serial: str, access_code: str) -> None:
        self.host = host
        self.serial = serial
        self.access_code = access_code
        self.sock: ssl.SSLSocket | None = None

    def connect(self) -> None:
        raw = socket.create_connection((self.host, PRINTER_PORTS["mqtt"]), timeout=4.0)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.sock = context.wrap_socket(raw, server_hostname=self.host)

        client_id = f"codex-local-{uuid.uuid4().hex[:10]}"
        variable = b"".join(
            (
                mqtt_string("MQTT"),
                bytes([4]),  # MQTT 3.1.1
                bytes([0xC2]),  # clean session + username + password
                struct.pack(">H", 60),
                mqtt_string(client_id),
                mqtt_string("bblp"),
                mqtt_string(self.access_code),
            )
        )
        self._send(bytes([0x10]) + mqtt_remaining_length(len(variable)) + variable)
        packet = self._read_packet()
        if len(packet) < 4 or packet[0] != 0x20 or packet[1] != 0x02 or packet[3] != 0x00:
            code = packet[3] if len(packet) > 3 else "unknown"
            raise RuntimeError(f"MQTT 登录失败，返回码: {code}")

    def publish_json(self, topic: str, payload: dict[str, Any]) -> None:
        encoded_topic = mqtt_string(topic)
        encoded_payload = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        variable = encoded_topic + encoded_payload
        self._send(bytes([0x30]) + mqtt_remaining_length(len(variable)) + variable)

    def close(self) -> None:
        if self.sock is not None:
            try:
                self._send(b"\xE0\x00")
            except OSError:
                pass
            try:
                self.sock.close()
            finally:
                self.sock = None

    def _send(self, data: bytes) -> None:
        if self.sock is None:
            raise RuntimeError("MQTT 未连接")
        self.sock.sendall(data)

    def _read_packet(self) -> bytes:
        if self.sock is None:
            raise RuntimeError("MQTT 未连接")
        first = self.sock.recv(1)
        if not first:
            raise RuntimeError("MQTT 连接在响应前关闭")
        multiplier = 1
        remaining = 0
        while True:
            raw = self.sock.recv(1)
            if not raw:
                raise RuntimeError("MQTT 响应长度不完整")
            digit = raw[0]
            remaining += (digit & 127) * multiplier
            if not digit & 128:
                break
            multiplier *= 128
            if multiplier > 128**3:
                raise RuntimeError("MQTT 响应长度无效")
        payload = b""
        while len(payload) < remaining:
            chunk = self.sock.recv(remaining - len(payload))
            if not chunk:
                raise RuntimeError("MQTT 响应数据不完整")
            payload += chunk
        return first + mqtt_remaining_length(remaining) + payload


def check_bambu_connection(fields: dict[str, str]) -> dict[str, Any]:
    config = load_local_config()
    ip = validate_printer_ip(first_value(fields, config, "ip", "printer_ip"))
    serial = first_value(fields, config, "serial", "printer_serial")
    access_code = first_value(fields, config, "access_code", "token")

    result: dict[str, Any] = {
        "ip": ip,
        "serialProvided": bool(serial),
        "accessCodeProvided": bool(access_code),
        "ports": {
            "mqtt": port_probe(ip, PRINTER_PORTS["mqtt"]),
            "ftps": port_probe(ip, PRINTER_PORTS["ftps"]),
        },
    }

    if serial and access_code and result["ports"]["mqtt"]["reachable"]:
        mqtt = BambuMQTT(ip, serial, access_code)
        try:
            mqtt.connect()
            result["mqttAuthenticated"] = True
        except (OSError, RuntimeError, ssl.SSLError) as exc:
            result["mqttAuthenticated"] = False
            result["mqttError"] = f"{type(exc).__name__}: {exc}"
        finally:
            mqtt.close()

    if access_code and result["ports"]["ftps"]["reachable"]:
        ftp: ImplicitFTP_TLS | None = None
        try:
            ftp = implicit_ftps_login(ip, access_code)
            result["ftpsAuthenticated"] = True
        except (OSError, ftplib.Error, ssl.SSLError) as exc:
            result["ftpsAuthenticated"] = False
            result["ftpsError"] = f"{type(exc).__name__}: {exc}"
        finally:
            if ftp is not None:
                try:
                    ftp.quit()
                except OSError:
                    ftp.close()
    return result


def send_project_file(fields: dict[str, str], filename: str, content: bytes) -> dict[str, Any]:
    config = load_local_config()
    ip = validate_printer_ip(first_value(fields, config, "ip", "printer_ip"))
    serial = first_value(fields, config, "serial", "printer_serial")
    access_code = first_value(fields, config, "access_code", "token")
    if not serial or not access_code:
        raise ValueError("发送打印任务需要打印机序列号和 LAN Access Code。")
    if not filename.lower().endswith(".gcode.3mf"):
        raise ValueError("直打入口只接受已切片的 .gcode.3mf；原始 STL 需要先切片。")

    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(filename).name)
    if not safe_name.lower().endswith(".gcode.3mf"):
        safe_name += ".gcode.3mf"
    job_name = f"codex_{int(time.time())}_{safe_name}"
    JOB_ROOT.mkdir(parents=True, exist_ok=True)
    local_job = JOB_ROOT / job_name
    local_job.write_bytes(content)
    checksum = hashlib.md5(content).hexdigest()

    ftp: ImplicitFTP_TLS | None = None
    mqtt: BambuMQTT | None = None
    try:
        ftp = implicit_ftps_login(ip, access_code)
        with local_job.open("rb") as stream:
            ftp.storbinary(f"STOR /cache/{job_name}", stream)

        use_ams = fields.get("use_ams", "false").lower() in {"1", "true", "yes", "on"}
        try:
            ams_slot = int(fields.get("ams_slot", "0"))
        except ValueError as exc:
            raise ValueError("AMS 槽位必须是 0–3 的整数。") from exc
        if use_ams and not 0 <= ams_slot <= 3:
            raise ValueError("AMS 槽位必须在 0–3。")

        ams_mapping: Any = [-1, -1, -1, -1, ams_slot] if use_ams else ""
        payload = {
            "print": {
                "sequence_id": str(int(time.time() * 1000) % 100000000),
                "command": "project_file",
                "param": "Metadata/plate_1.gcode",
                "project_id": "0",
                "profile_id": "0",
                "task_id": "0",
                "subtask_id": "0",
                "subtask_name": job_name,
                "file": job_name,
                "url": f"ftp:///cache/{job_name}",
                "md5": checksum,
                "timelapse": False,
                "bed_type": "auto",
                "bed_levelling": True,
                "flow_cali": True,
                "vibration_cali": True,
                "layer_inspect": True,
                "use_ams": use_ams,
                "ams_mapping": ams_mapping,
            }
        }
        mqtt = BambuMQTT(ip, serial, access_code)
        mqtt.connect()
        mqtt.publish_json(f"device/{serial}/request", payload)
        return {
            "accepted": True,
            "localJob": str(local_job.relative_to(PROJECT_ROOT)),
            "printerFile": f"/cache/{job_name}",
            "md5": checksum,
        }
    finally:
        if mqtt is not None:
            mqtt.close()
        if ftp is not None:
            try:
                ftp.quit()
            except OSError:
                ftp.close()


def find_slicer(config: dict[str, Any]) -> Path | None:
    configured = config.get("slicer_path", "")
    candidates = []
    if isinstance(configured, str) and configured.strip():
        candidates.append(Path(configured.strip()))
    candidates.extend(
        (
            Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"),
            Path("/Applications/Bambu Studio.app/Contents/MacOS/Bambu Studio"),
        )
    )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def open_in_slicer(asset_name: str) -> dict[str, Any]:
    asset = safe_asset(STL_ROOT, asset_name)
    slicer = find_slicer(load_local_config())
    if slicer is None:
        raise FileNotFoundError(
            "没有检测到 Bambu Studio。请安装后再试，或直接下载 STL 导入切片器。"
        )
    subprocess.Popen([str(slicer), str(asset)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"opened": True, "slicer": str(slicer), "asset": asset.name}


class PreviewHandler(BaseHTTPRequestHandler):
    server_version = "OKLensBox/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        # Keep credentials and large request bodies out of the terminal log.
        print(f"[{self.log_date_time_string()}] {format % args}")

    def _headers(self, content_type: str, length: int | None = None) -> None:
        self.send_header("Content-Type", content_type)
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")

    def send_json(self, value: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._headers("application/json; charset=utf-8", len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def send_file(self, path: Path, download: bool = False, head_only: bool = False) -> None:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix.lower() == ".stl":
            content_type = "model/stl"
        payload_length = path.stat().st_size
        self.send_response(HTTPStatus.OK)
        self._headers(content_type, payload_length)
        if download:
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.name)
            self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')
        self.end_headers()
        if head_only:
            return
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/assets/"):
                asset = safe_asset(STL_ROOT, parsed.path.removeprefix("/assets/"))
                self.send_file(asset, download=("download" in parsed.query), head_only=True)
                return
            if parsed.path.startswith("/previews/"):
                preview = safe_asset(PREVIEW_ROOT, parsed.path.removeprefix("/previews/"))
                self.send_file(preview, head_only=True)
                return
            relative = parsed.path.removeprefix("/") or "index.html"
            self.send_file(safe_asset(WEB_ROOT, relative), head_only=True)
        except FileNotFoundError:
            self.send_json({"ok": False, "error": "找不到资源。"}, HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/health":
                config = load_local_config()
                slicer = find_slicer(config)
                self.send_json(
                    {
                        "ok": True,
                        "model": MODEL_INFO,
                        "slicerDetected": str(slicer) if slicer else None,
                        "configFilePresent": LOCAL_CONFIG.is_file(),
                    }
                )
                return
            if parsed.path == "/api/model":
                self.send_json(MODEL_INFO)
                return
            if parsed.path.startswith("/assets/"):
                asset = safe_asset(STL_ROOT, parsed.path.removeprefix("/assets/"))
                self.send_file(asset, download=("download" in parsed.query))
                return
            if parsed.path.startswith("/previews/"):
                preview = safe_asset(PREVIEW_ROOT, parsed.path.removeprefix("/previews/"))
                self.send_file(preview)
                return

            relative = parsed.path.removeprefix("/") or "index.html"
            self.send_file(safe_asset(WEB_ROOT, relative))
        except FileNotFoundError:
            self.send_json({"ok": False, "error": "找不到资源。"}, HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except (OSError, PermissionError) as exc:
            self.send_json({"ok": False, "error": f"读取资源失败：{exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/printer/test":
                fields = parse_json_body(self)
                normalized = {key: str(value) for key, value in fields.items() if value is not None}
                self.send_json({"ok": True, "result": check_bambu_connection(normalized)})
                return
            if parsed.path == "/api/open-slicer":
                fields = parse_json_body(self)
                asset_name = str(fields.get("asset", MODEL_INFO["printAsset"]))
                self.send_json({"ok": True, "result": open_in_slicer(asset_name)})
                return
            if parsed.path == "/api/print":
                content_type = self.headers.get("Content-Type", "")
                fields, files = parse_multipart(read_request_body(self), content_type)
                if "file" not in files:
                    raise ValueError("请选择一个已切片的 .gcode.3mf 文件。")
                filename, content = files["file"]
                if not content:
                    raise ValueError("上传文件为空。")
                self.send_json({"ok": True, "result": send_project_file(fields, filename, content)})
                return
            self.send_json({"ok": False, "error": "未知 API 路径。"}, HTTPStatus.NOT_FOUND)
        except (ValueError, FileNotFoundError) as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except (OSError, ftplib.Error, RuntimeError, ssl.SSLError) as exc:
            self.send_json(
                {"ok": False, "error": f"局域网操作未完成：{type(exc).__name__}: {exc}"},
                HTTPStatus.BAD_GATEWAY,
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the OK lens box preview and optional Bambu LAN bridge.")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址；局域网访问使用 0.0.0.0")
    parser.add_argument("--port", type=int, default=8765, help="HTTP 端口")
    args = parser.parse_args()

    if not WEB_ROOT.is_dir():
        parser.error(f"缺少网页目录: {WEB_ROOT}")
    server = ThreadingHTTPServer((args.host, args.port), PreviewHandler)
    print(f"Preview server: http://{args.host}:{args.port}/")
    print("Press Ctrl-C to stop. Credentials are kept in request memory only.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping preview server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
