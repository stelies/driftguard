"""`driftguard report`: inject scan.json (+ findings.json) into the single-file UI template -> report.html.

The template (driftguard/report/template.html) is built from web/ (`npm run build`) and holds the placeholder
`__DG_DATA__` inside <script id="dg-data" type="application/json">. No network, no LLM, stdlib only.
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

from . import paths

PLACEHOLDER = "__DG_DATA__"
TEMPLATE = Path(__file__).with_name("report") / "template.html"
# Session fields the UI never reads; dropping them keeps the file small and keeps local paths out of it.
_DROP = {"source", "files", "todos", "cwd", "prompts", "usage"}


def template_text() -> str:
    try:
        return TEMPLATE.read_text(encoding="utf-8")
    except OSError:
        print(f"driftguard report: UI template missing ({TEMPLATE}). Build it: cd web && npm install && npm run build", file=sys.stderr)
        raise SystemExit(2)


def build_data(scan: dict, findings: dict | None = None) -> dict:
    """The object the UI reads: scan fields + merged findings (may be empty)."""
    sessions = [{k: v for k, v in s.items() if k not in _DROP} for s in scan.get("sessions", [])]
    return {
        "generated": scan.get("generated", ""), "version": scan.get("version", ""), "setup": scan.get("setup", {}),
        "mode": scan.get("mode", {}), "summary": scan.get("summary", {}), "sessions": sessions,
        "blocks": scan.get("blocks", []), "findings": findings or {},
    }


def dumps_for_html(data: dict) -> str:
    """JSON that is safe inside <script type="application/json">: `</` and `<!--` cannot close or confuse the tag."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\u0021--")


def inject(template: str, data: dict) -> str:
    if PLACEHOLDER not in template:
        raise ValueError("template has no __DG_DATA__ placeholder")
    return template.replace(PLACEHOLDER, dumps_for_html(data), 1)


def render(scan: dict, findings: dict | None = None, template: str | None = None) -> str:
    return inject(template if template is not None else template_text(), build_data(scan, findings))


def _load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def build(out: Path | None = None) -> Path:
    d = paths.data_dir()
    scan = _load_json(d / "scan.json")
    if not isinstance(scan, dict):
        print("driftguard report: no scan data yet. Run `driftguard scan` first.", file=sys.stderr)
        raise SystemExit(1)
    findings = _load_json(d / "findings.json")
    out = out or d / "report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(scan, findings if isinstance(findings, dict) else None), encoding="utf-8")
    note = "" if findings else " (no findings yet: run the agent pass, /driftguard, for verdicts)"
    print(f"wrote {out}{note}")
    return out


def _free_port(start: int, host: str, exact: bool) -> int:
    for p in ([start] if exact else range(start, start + 50)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    print(f"driftguard report: port {start} is busy" if exact else "driftguard report: no free port in 5191-5240", file=sys.stderr)
    raise SystemExit(1)


def _lan_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return None


def _open(url: str) -> None:
    try:
        if "microsoft" in os.uname().release.lower() and shutil.which("wslview"):
            subprocess.Popen(["wslview", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    except (AttributeError, OSError):
        pass
    webbrowser.open(url)


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):  # keep the terminal clean
        pass


def serve(html_file: Path, port: int, lan: bool, open_browser: bool) -> int:
    host = "0.0.0.0" if lan else "127.0.0.1"
    port = _free_port(port or 5191, host, exact=bool(port))
    # Serve a private temp dir holding only the report, never ~/.driftguard (it holds scan.json with your prompts).
    root = Path(tempfile.mkdtemp(prefix="dg-report-"))
    shutil.copyfile(html_file, root / "index.html")
    srv = http.server.ThreadingHTTPServer((host, port), functools.partial(_Quiet, directory=str(root)))
    urls = [f"http://127.0.0.1:{port}/"]
    if lan and _lan_ip():
        urls.append(f"http://{_lan_ip()}:{port}/")
    print("serving " + "  ".join(urls) + "   (Ctrl-C to stop)", flush=True)
    if open_browser:
        threading.Timer(0.3, _open, args=(urls[0],)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        srv.server_close()
        shutil.rmtree(root, ignore_errors=True)
    return 0


def run(args) -> int:
    out = build(Path(args.out).expanduser() if getattr(args, "out", None) else None)
    if getattr(args, "serve", False):
        return serve(out, getattr(args, "port", 0), getattr(args, "lan", False), not getattr(args, "no_open", False))
    return 0
