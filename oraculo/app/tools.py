import json
import os
import socket
import ssl
import urllib.error
import urllib.request

from pymodbus.client import ModbusTcpClient

OPENPLC_HOST = "openplc"
MODBUS_PORT = 502
MODBUS_SLAVE = 1
KNOWLEDGE_DIR = "/app/knowledge"
MAX_FILE_CHARS = 100000

HTTP_SERVICES = [
    ("openplc", "http://openplc:8080"),
    ("hmi (fuxa)", "http://hmi:1881"),
]
HTTPS_SERVICES = [
    ("opensearch", "https://opensearch:9200"),
]
TCP_SERVICES = [
    ("mosquitto", "mosquitto", 1883),
]


def read_modbus(address, count=1, register_type="holding"):
    count = max(1, min(int(count), 125))
    address = int(address)
    client = ModbusTcpClient(OPENPLC_HOST, port=MODBUS_PORT)
    try:
        if not client.connect():
            return {"error": f"cannot connect to {OPENPLC_HOST}:{MODBUS_PORT}"}
        if register_type == "coil":
            rr = client.read_coils(address, count=count, slave=MODBUS_SLAVE)
            if rr.isError():
                return {"error": str(rr)}
            values = [bool(b) for b in rr.bits[:count]]
        else:
            rr = client.read_holding_registers(address, count=count, slave=MODBUS_SLAVE)
            if rr.isError():
                return {"error": str(rr)}
            values = rr.registers
        return {
            "address": address,
            "type": register_type,
            "count": count,
            "values": values,
        }
    except Exception as e:
        return {"error": f"modbus read failed: {e}"}
    finally:
        client.close()


def check_services():
    results = {}
    for name, url in HTTP_SERVICES:
        results[name] = _http_probe(url)
    for name, url in HTTPS_SERVICES:
        results[name] = _https_probe(url, "opensearch")
    for name, host, port in TCP_SERVICES:
        try:
            with socket.create_connection((host, port), timeout=4):
                pass
            results[name] = {"status": "up"}
        except Exception as e:
            results[name] = {"status": "down", "error": str(e)}
    return results


def _http_probe(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "oraculo"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            return {"status": "up", "http_code": resp.status}
    except urllib.error.HTTPError as e:
        return {"status": "up", "http_code": e.code}
    except Exception as e:
        return {"status": "down", "error": str(e)}


def _https_probe(url, name):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "oraculo"})
        with urllib.request.urlopen(req, timeout=4, context=context) as resp:
            return {"status": "up", "http_code": resp.status}
    except urllib.error.HTTPError as e:
        return {"status": "up", "http_code": e.code}
    except Exception:
        fallback = _http_probe(f"http://{name}:9200")
        if fallback["status"] == "up":
            fallback["note"] = "answered over plain http"
        return fallback


def list_config_files():
    entries = []
    for root, dirs, files in os.walk(KNOWLEDGE_DIR):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            path = os.path.join(root, name)
            entries.append(
                {
                    "path": os.path.relpath(path, KNOWLEDGE_DIR),
                    "bytes": os.path.getsize(path),
                }
            )
    return entries


def read_config_file(path):
    rel = os.path.normpath(str(path)).lstrip("/")
    full = os.path.join(KNOWLEDGE_DIR, rel)
    if not os.path.abspath(full).startswith(os.path.abspath(KNOWLEDGE_DIR)):
        return {"error": "access denied: path outside knowledge directory"}
    if not os.path.isfile(full):
        return {"error": f"file not found: {rel} (use list_config_files)"}
    size = os.path.getsize(full)
    with open(full, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read(MAX_FILE_CHARS)
    out = {"path": rel, "bytes": size, "content": content}
    if len(content) < size:
        out["note"] = f"truncated to first {len(content)} chars of {size}"
    return out


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_modbus",
            "description": (
                "Read live values from the OpenPLC Modbus TCP server (slave 1). "
                "Read-only. Holding registers 100-129 hold tank data (capacity, "
                "pressure, temp, heat_cool_level per FACTORY.md); coils 800-823 hold "
                "valve command/status pairs and belt1_onoff (818); coil 1599 is "
                "manual_mode (0=automatic, 1=manual)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "integer",
                        "description": "Starting address (0-based coil/register number)",
                    },
                    "count": {
                        "type": "integer",
                        "description": "How many consecutive values to read (default 1)",
                    },
                    "register_type": {
                        "type": "string",
                        "enum": ["holding", "coil"],
                        "description": "Read holding registers or coils (default holding)",
                    },
                },
                "required": ["address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_services",
            "description": (
                "Check whether the factory services are reachable right now: "
                "OpenPLC web UI (:8080), FUXA HMI (:1881), OpenSearch (:9200), "
                "Mosquitto MQTT (:1883). Returns up/down per service."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_config_files",
            "description": (
                "List the configuration/documentation files mounted into the agent "
                "(factory docs, simulator JSONs, OpenPLC script.st, mosquitto.conf, "
                "FUXA project). Returns paths and sizes."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_config_file",
            "description": (
                "Read one file from the mounted knowledge directory by relative path "
                "(see list_config_files). Use this to inspect configs such as "
                "flamingmoes/fuxa/fuxa-project.json or a simulator JSON."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path, e.g. flamingmoes/openplc/config/script.st",
                    }
                },
                "required": ["path"],
            },
        },
    },
]


def dispatch(name, args):
    try:
        if name == "read_modbus":
            address = args.get("address")
            if address is None:
                return {"error": "missing required parameter: address"}
            return read_modbus(
                address=address,
                count=args.get("count", 1),
                register_type=args.get("register_type", "holding"),
            )
        if name == "check_services":
            return check_services()
        if name == "list_config_files":
            return list_config_files()
        if name == "read_config_file":
            return read_config_file(args.get("path", ""))
        return {"error": f"unknown tool: {name}"}
    except Exception as e:
        return {"error": str(e)}
