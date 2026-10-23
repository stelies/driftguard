"""Cursor: composer chats in state.vscdb (sqlite, table cursorDiskKV). Best effort, read-only."""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from typing import List

from .. import paths
from ..schema import Session, empty_tokens
from . import common

_warned = False


def discover() -> List[str]:
    return [str(p) for p in paths.cursor_dbs()]


def _iso(ms) -> str:
    try:
        return datetime.fromtimestamp(float(ms) / 1000, timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def _j(v):
    try:
        if isinstance(v, bytes):
            v = v.decode("utf-8", "ignore")
        return json.loads(v)
    except (TypeError, ValueError):
        return None


def _parse(path: str) -> List[Session]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    try:
        rows = con.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%'").fetchall()
        out: List[Session] = []
        for key, val in rows:
            d = _j(val)
            if not isinstance(d, dict):
                continue
            cid = d.get("composerId") or key.split(":", 1)[1]
            msgs = d.get("conversation")
            if not isinstance(msgs, list) or not msgs:
                msgs = []
                for h in d.get("fullConversationHeadersOnly") or []:
                    bid = h.get("bubbleId") if isinstance(h, dict) else None
                    if not bid:
                        continue
                    r = con.execute("SELECT value FROM cursorDiskKV WHERE key=?", (f"bubbleId:{cid}:{bid}",)).fetchone()
                    b = _j(r[0]) if r else None
                    if isinstance(b, dict):
                        msgs.append(b)
            s: Session = {"agent": "cursor", "id": cid, "source": path, "prompts": [], "tools": 0, "tokens": empty_tokens(),
                          "models": {}, "usage": [], "files": [], "todos": [], "title": d.get("name") or ""}
            t0, t1 = _iso(d.get("createdAt")), _iso(d.get("lastUpdatedAt") or d.get("createdAt"))
            for b in msgs:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == 1:
                    txt = common.clean_prompt(str(b.get("text") or ""))
                    if txt and not common.is_skip(txt):
                        s["prompts"].append({"t": t0, "txt": txt})
                elif b.get("type") == 2:
                    tc = b.get("tokenCount")
                    if isinstance(tc, dict):
                        s["tokens"]["input"] += int(tc.get("inputTokens") or 0)
                        s["tokens"]["output"] += int(tc.get("outputTokens") or 0)
            if not t0 or not s["prompts"]:
                continue
            s["start"], s["end"] = t0, t1 or t0
            s["project"] = "cursor"
            s["bot"] = False
            out.append(s)
        return out
    finally:
        con.close()


def parse(path: str) -> List[Session]:
    global _warned
    try:
        return _parse(path)
    except Exception as e:  # locked db, schema change, corrupt file: never break a scan
        if not _warned:
            _warned = True
            print(f"driftguard: could not read Cursor db ({type(e).__name__}); skipping", file=sys.stderr)
        return []
