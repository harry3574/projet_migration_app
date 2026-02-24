import importlib
import subprocess
import json
import sys
from pathlib import Path
from app.registry import registry

PYTHON32 = Path("python32/python.exe")
RUNNER32 = Path("python32/runner.py")


def execute(module_id: str, payload: dict, mode="sync", format=None):

    meta = registry.modules[module_id]["meta"]
    interpreter = meta.get("interpreter", "64")

    if interpreter == "32":
        return execute_32(module_id, payload, mode, format)

    return execute_64(module_id, payload, mode, format)


def execute_64(module_id, payload, mode, format):

    module = importlib.import_module(f"modules.{module_id}.module")

    if mode == "stream":
        return module.stream(payload)

    if mode == "download":
        return module.download(payload, format=format)

    return module.run(payload)


def execute_32(module_id, payload, mode, format):

    req = {
        "module_id": module_id,
        "payload": payload,
        "mode": mode,
        "format": format
    }

    proc = subprocess.Popen(
        [str(PYTHON32), str(RUNNER32)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout, stderr = proc.communicate(json.dumps(req))

    if proc.returncode != 0:
        raise RuntimeError(stderr)

    resp = json.loads(stdout)

    if not resp["success"]:
        raise RuntimeError(resp["error"])

    return resp["result"]
