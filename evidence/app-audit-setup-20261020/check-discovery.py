"""Check local skill metadata only; no thread, model turn, or provider request."""

import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading


root = Path(__file__).resolve().parents[2]
node = shutil.which("node")
codex_entry = Path(os.environ["APPDATA"]) / "npm/node_modules/@openai/codex/bin/codex.js"
if not node or not codex_entry.is_file():
    raise SystemExit("This check requires the installed Node/npm Codex CLI.")

command = [
    node, str(codex_entry),
    "-c", "analytics.enabled=false",
    "-c", "service_tier=flex",  # Metadata-only compatibility with CLI 0.128.0.
    "app-server", "--listen", "stdio://",
]
process = subprocess.Popen(
    command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
    creationflags=subprocess.CREATE_NO_WINDOW,
)
events = queue.Queue()


def read_events():
    for line in process.stdout:
        try:
            events.put(json.loads(line))
        except json.JSONDecodeError:
            continue


def send(message):
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()


def request(identifier, method, params):
    send({"jsonrpc": "2.0", "id": identifier, "method": method, "params": params})
    while True:
        event = events.get(timeout=30)
        if event.get("id") == identifier:
            if "error" in event:
                raise RuntimeError(event["error"])
            return event["result"]


threading.Thread(target=read_events, daemon=True).start()
try:
    request(1, "initialize", {
        "clientInfo": {"name": "app-audit-local-discovery", "version": "1.0.0"},
    })
    send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
    result = request(2, "skills/list", {
        "cwds": [str(root), str(root.parent)], "forceReload": True,
    })
    expected = {"app-audit", "playwright", "impeccable"}
    filtered = []
    for entry in result["data"]:
        selected = [
            {key: skill[key] for key in ("name", "path", "scope", "enabled")}
            for skill in entry["skills"] if skill["name"] in expected
        ]
        if len(selected) != 3 or {skill["name"] for skill in selected} != expected:
            raise RuntimeError(f"Missing or duplicate audit skill in {entry['cwd']}")
        if entry.get("errors") or not all(skill["enabled"] for skill in selected):
            raise RuntimeError(f"Disabled skill or discovery error in {entry['cwd']}")
        filtered.append({"cwd": entry["cwd"], "skills": selected, "error_count": 0})
    if {Path(item["cwd"]) for item in filtered} != {root, root.parent}:
        raise RuntimeError("Discovery did not return both workspace locations.")
    output = json.dumps(filtered, indent=2) + "\n"
    Path(__file__).with_name("discovery.json").write_text(output, encoding="utf-8")
    print(output)
finally:
    process.terminate()
    process.wait(timeout=10)
