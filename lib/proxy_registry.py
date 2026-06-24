"""Proxy registry for patchright-mcp-bridge.

Stores proxy configurations that AI can query and use.
File: ~/.patchright-mcp/proxies.json
"""
import json
import os
from typing import Optional
from dataclasses import dataclass, asdict

ROOT = os.environ.get("PATCHRIGHT_MCP_HOME") or os.path.expanduser("~/.patchright-mcp")
PROXIES_FILE = os.path.join(ROOT, "proxies.json")


@dataclass
class Proxy:
    """Proxy configuration."""
    name: str
    server: str           # host:port or scheme://host:port
    username: str = ""
    password: str = ""
    scheme: str = "http"  # http, https, socks5, socks5h
    bypass: str = ""      # comma-separated bypass list
    description: str = ""


def _load() -> dict:
    if not os.path.isfile(PROXIES_FILE):
        return {"version": 1, "proxies": {}}
    with open(PROXIES_FILE) as f:
        return json.load(f)


def _save(data: dict):
    os.makedirs(os.path.dirname(PROXIES_FILE), exist_ok=True)
    tmp = PROXIES_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, PROXIES_FILE)


def add_proxy(name: str, server: str, username: str = "", password: str = "",
              scheme: str = "http", bypass: str = "", description: str = "") -> Proxy:
    """Add or update a proxy."""
    proxy = Proxy(
        name=name,
        server=server,
        username=username,
        password=password,
        scheme=scheme,
        bypass=bypass,
        description=description,
    )
    data = _load()
    data["proxies"][name] = asdict(proxy)
    _save(data)
    return proxy


def get_proxy(name: str) -> Optional[Proxy]:
    """Get proxy by name."""
    data = _load()
    entry = data.get("proxies", {}).get(name)
    if not entry:
        return None
    return Proxy(**entry)


def list_proxies() -> list[dict]:
    """List all proxies (passwords hidden)."""
    data = _load()
    result = []
    for name, entry in data.get("proxies", {}).items():
        safe = dict(entry)
        if safe.get("password"):
            safe["password"] = "***"
        result.append(safe)
    return result


def delete_proxy(name: str) -> bool:
    """Delete a proxy."""
    data = _load()
    if name in data.get("proxies", {}):
        del data["proxies"][name]
        _save(data)
        return True
    return False


def to_chromium_args(proxy: Proxy) -> list[str]:
    """Convert proxy to Chromium launch args."""
    args = []
    host_port = proxy.server
    if "://" in proxy.server:
        from urllib.parse import urlparse
        p = urlparse(proxy.server)
        host_port = f"{p.hostname}:{p.port or 8080}"
    
    args.append(f"--proxy-server={proxy.scheme}://{host_port}")
    
    if proxy.bypass:
        args.append(f"--proxy-bypass-list={proxy.bypass}")
    
    return args


def to_proxy_auth(proxy: Proxy) -> Optional[dict]:
    """Convert proxy to auth dict for CDP injection."""
    if proxy.username:
        return {"username": proxy.username, "password": proxy.password}
    return None
