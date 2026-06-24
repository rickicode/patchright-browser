#!/usr/bin/env python3
"""Patchright Browser Dashboard — profiles, health, tabs.
Password-protected, public-facing.
Run: python3 dashboard.py
Access: http://0.0.0.0:9878
"""
import asyncio
import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

PATCHRIGHT_URL = "http://127.0.0.1:9877/mcp/"
PORT = 9878
PASSWORD = "hijilabs7"
JAKARTA = timezone(timedelta(hours=7))

# Session tokens (in-memory, resets on restart)
_sessions = {}
SESSION_TTL = 86400  # 24h


def make_token():
    return secrets.token_hex(32)


def check_auth(handler):
    """Check if request has valid session. Returns True if authorized."""
    cookie = handler.headers.get("Cookie", "")
    token = None
    for part in cookie.split(";"):
        k, _, v = part.strip().partition("=")
        if k == "session":
            token = v
            break
    if token and token in _sessions:
        if time.time() - _sessions[token] < SESSION_TTL:
            _sessions[token] = time.time()  # refresh
            return True
        del _sessions[token]
    return False


def call_patchright(tool, arguments=None):
    """Call Patchright MCP tool via StreamableHTTP."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async def _call():
        async with streamablehttp_client(PATCHRIGHT_URL) as (rs, ws, _):
            async with ClientSession(rs, ws) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments=arguments or {})
                for item in result.content:
                    if hasattr(item, 'text'):
                        text = item.text
                        # Try direct JSON first
                        try:
                            data = json.loads(text)
                            # If it has 'content' wrapper, dig deeper
                            if 'content' in data and isinstance(data['content'], list):
                                for inner in data['content']:
                                    if inner.get('type') == 'text':
                                        inner_text = inner['text']
                                        if '### Result\n' in inner_text:
                                            json_str = inner_text.split('### Result\n')[1].split('\n###')[0].strip()
                                            return json.loads(json_str)
                            # Otherwise return directly
                            return data
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass
                        # Try ### Result pattern directly
                        if '### Result\n' in text:
                            try:
                                json_str = text.split('### Result\n')[1].split('\n###')[0].strip()
                                return json.loads(json_str)
                            except (json.JSONDecodeError, IndexError):
                                pass
                return None
    return asyncio.run(_call())


def get_profiles():
    result = call_patchright("profile_list")
    if result and 'profiles' in result:
        return result
    return {"default": "unknown", "profiles": []}


def get_health(profile):
    return call_patchright("browser_health", {"profile": profile})


def get_tabs(profile):
    return call_patchright("browser_tabs", {"action": "list", "profile": profile})


def format_ts(ts):
    if not ts:
        return "Never"
    dt = datetime.fromtimestamp(ts, tz=JAKARTA)
    return dt.strftime("%Y-%m-%d %H:%M:%S GMT+7")


def format_uptime(seconds):
    if not seconds:
        return "Offline"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m}m" if h > 0 else f"{m}m"


LOGIN_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login — Patchright Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap" media="print" onload="this.media='all'">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0a12;--surface:#111119;--card:#15151f;--border:#1e1e30;--pri:#ff2d78;--txt:#e0e0f0;--txt2:#8888a8;--r:12px}
body{background:var(--bg);color:var(--txt);font-family:'Inter',system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh}
.login{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:32px;width:100%;max-width:360px}
h1{font-size:1.2em;margin-bottom:8px;display:flex;align-items:center;gap:8px}
h1 svg{width:20px;height:20px;color:var(--pri)}
.sub{font-size:.78em;color:var(--txt2);margin-bottom:24px}
.field{margin-bottom:16px}
.field label{display:block;font-size:.68em;color:var(--txt2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.field input{width:100%;padding:10px 14px;border-radius:8px;border:1.5px solid var(--border);background:var(--surface);color:var(--txt);font-size:.9em;font-family:inherit;outline:none;transition:border .15s}
.field input:focus{border-color:var(--pri)}
.btn{width:100%;padding:11px;border-radius:8px;border:none;background:linear-gradient(135deg,#ff2d78,#e91e6c);color:#0a0a12;font-size:.88em;font-weight:700;cursor:pointer;font-family:inherit;transition:opacity .15s}
.btn:hover{opacity:.85}
.err{color:#ff5252;font-size:.78em;margin-bottom:12px;display:none}
</style>
</head>
<body>
<div class="login">
  <h1>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="21.17" x2="12" y1="8" y2="8"/><line x1="3.95" x2="8.54" y1="6.06" y2="14"/><line x1="10.88" x2="15.46" y1="21.94" y2="14"/></svg>
    Patchright Dashboard
  </h1>
  <div class="sub">Enter password to continue</div>
  <div class="err" id="err">Invalid password</div>
  <form method="POST" action="/login">
    <div class="field">
      <label>Password</label>
      <input type="password" name="password" autofocus required>
    </div>
    <button class="btn" type="submit">Login</button>
  </form>
</div>
</body>
</html>'''


def build_html():
    profiles_data = get_profiles()
    profiles = profiles_data.get("profiles", [])

    cards = []
    for p in profiles:
        name = p.get("name", "")
        alive = p.get("alive", False)
        alive_modes = p.get("alive_modes", [])
        last_used = p.get("last_used_at")
        uptime = p.get("uptime_seconds", 0)
        is_default = p.get("is_default", False)
        desc = p.get("description", "")
        caps = p.get("caps", [])
        viewport = p.get("viewport", {})

        health = None
        tabs = []
        if alive:
            health = get_health(name)
            tabs_data = get_tabs(name)
            if tabs_data:
                tabs = tabs_data if isinstance(tabs_data, list) else []

        status_color = "#00e676" if alive else "#ff5252"
        status_text = "Online" if alive else "Offline"
        mode_text = ", ".join(alive_modes) if alive_modes else "—"

        tab_rows = ""
        if tabs:
            for i, tab in enumerate(tabs):
                url = tab.get("url", "") if isinstance(tab, dict) else str(tab)
                title = tab.get("title", "") if isinstance(tab, dict) else ""
                tab_rows += f'<div class="tab"><span class="tab-idx">{i}</span> <span class="tab-title">{title[:50]}</span> <span class="tab-url">{url[:60]}</span></div>'
        else:
            tab_rows = '<div class="tab-empty">No active tabs</div>'

        badge = '<span class="badge default">DEFAULT</span>' if is_default else ''
        cap_badges = "".join(f'<span class="badge cap">{c}</span>' for c in caps) if caps else '<span class="badge none">none</span>'

        cards.append(f'''
        <div class="card {'alive' if alive else 'dead'}">
          <div class="card-header">
            <div class="card-title">
              <span class="status-dot" style="background:{status_color}"></span>
              <h3>{name}</h3>
              {badge}
            </div>
            <span class="status-text" style="color:{status_color}">{status_text}</span>
          </div>
          <div class="card-body">
            <div class="info-grid">
              <div class="info"><label>Mode</label><value>{mode_text}</value></div>
              <div class="info"><label>Uptime</label><value>{format_uptime(uptime)}</value></div>
              <div class="info"><label>Last Used</label><value>{format_ts(last_used)}</value></div>
              <div class="info"><label>Viewport</label><value>{viewport.get('width', '?')}×{viewport.get('height', '?')}</value></div>
              <div class="info"><label>Caps</label><value>{cap_badges}</value></div>
              <div class="info"><label>Description</label><value>{desc or '—'}</value></div>
            </div>
            <div class="tabs-section">
              <label>Active Tabs</label>
              {tab_rows}
            </div>
          </div>
        </div>
        ''')

    now = datetime.now(JAKARTA).strftime("%Y-%m-%d %H:%M:%S GMT+7")

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Patchright Browser Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap" media="print" onload="this.media='all'">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
a{{text-decoration:none;color:inherit}}
:root{{--bg:#0a0a12;--surface:#111119;--card:#15151f;--border:#1e1e30;--pri:#ff2d78;--ok:#00e676;--red:#ff5252;--txt:#e0e0f0;--txt2:#8888a8;--txt3:#555570;--r:12px}}
body{{background:var(--bg);color:var(--txt);font-family:'Inter',system-ui,sans-serif;padding:24px}}
.header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}}
.header h1{{font-size:1.4em;font-weight:700;display:flex;align-items:center;gap:10px}}
.header h1 svg{{width:24px;height:24px;color:var(--pri)}}
.ts{{font-size:.75em;color:var(--txt3);font-family:'JetBrains Mono',monospace}}
.logout{{font-size:.75em;color:var(--txt3);cursor:pointer;padding:4px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface)}}
.logout:hover{{border-color:var(--pri);color:var(--pri)}}
.grid{{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(400px,1fr))}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:var(--r);overflow:hidden}}
.card.alive{{border-color:rgba(0,230,118,.2)}}
.card.dead{{border-color:rgba(255,82,82,.15)}}
.card-header{{padding:16px 20px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border)}}
.card-title{{display:flex;align-items:center;gap:10px}}
.card-title h3{{font-size:1.1em;font-weight:700}}
.status-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.status-text{{font-size:.78em;font-weight:600;font-family:'JetBrains Mono',monospace}}
.badge{{font-size:.62em;padding:2px 8px;border-radius:12px;font-weight:600;text-transform:uppercase;letter-spacing:.3px}}
.badge.default{{background:rgba(255,45,120,.12);color:var(--pri);border:1px solid rgba(255,45,120,.2)}}
.badge.cap{{background:rgba(0,230,118,.08);color:var(--ok);border:1px solid rgba(0,230,118,.15)}}
.badge.none{{background:rgba(136,136,168,.08);color:var(--txt2);border:1px solid var(--border)}}
.card-body{{padding:16px 20px}}
.info-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px}}
.info label{{display:block;font-size:.62em;color:var(--txt3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}}
.info value{{font-size:.85em;color:var(--txt2)}}
.tabs-section{{border-top:1px solid var(--border);padding-top:12px}}
.tabs-section>label{{display:block;font-size:.62em;color:var(--txt3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}}
.tab{{display:flex;align-items:center;gap:8px;padding:6px 0;font-size:.78em;color:var(--txt2)}}
.tab-idx{{background:var(--surface);padding:1px 6px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:.7em;color:var(--txt3)}}
.tab-title{{font-weight:500;color:var(--txt);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.tab-url{{color:var(--txt3);font-family:'JetBrains Mono',monospace;font-size:.7em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.tab-empty{{font-size:.78em;color:var(--txt3);font-style:italic}}
@media(max-width:600px){{.info-grid{{grid-template-columns:1fr 1fr}}.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="header">
  <h1>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="21.17" x2="12" y1="8" y2="8"/><line x1="3.95" x2="8.54" y1="6.06" y2="14"/><line x1="10.88" x2="15.46" y1="21.94" y2="14"/></svg>
    Patchright Browser Dashboard
  </h1>
  <div style="display:flex;align-items:center;gap:12px">
    <span class="ts">{now}</span>
    <a href="/logout" class="logout">Logout</a>
  </div>
</div>
<div class="grid">
{"".join(cards)}
</div>
</body>
</html>'''


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/logout":
            cookie = self.headers.get("Cookie", "")
            for part in cookie.split(";"):
                k, _, v = part.strip().partition("=")
                if k == "session" and v in _sessions:
                    del _sessions[v]
            self.send_response(302)
            self.send_header("Set-Cookie", "session=; Path=/; Max-Age=0")
            self.send_header("Location", "/")
            self.end_headers()
            return

        if parsed.path == "/login":
            if check_auth(self):
                self.send_response(302)
                self.send_header("Location", "/")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(LOGIN_HTML.encode())
            return

        if not check_auth(self):
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
            return

        if parsed.path == "/" or parsed.path == "/index.html":
            html = build_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())
        elif parsed.path == "/api/profiles":
            data = get_profiles()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/login":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            params = parse_qs(body)
            pw = params.get("password", [""])[0]

            if pw == PASSWORD:
                token = make_token()
                _sessions[token] = time.time()
                self.send_response(302)
                self.send_header("Set-Cookie", f"session={token}; Path=/; Max-Age={SESSION_TTL}; HttpOnly; SameSite=Strict")
                self.send_header("Location", "/")
                self.end_headers()
                return

            # Wrong password — show login with error
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = LOGIN_HTML.replace('display:none', 'display:block')
            self.wfile.write(html.encode())
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    print(f"Patchright Dashboard: http://0.0.0.0:{PORT}")
    print(f"Password: {'*' * len(PASSWORD)}")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()
