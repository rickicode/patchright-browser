"""Rich profile schema for patchright-mcp-bridge.

A Profile is a persistent browser context: cookies, storage, login state,
fingerprint settings. The bridge maps one Profile to one patchright-mcp
subprocess.

This module is pure data (no I/O). Use registry.py for read/write.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Literal, Optional
from urllib.parse import urlparse

ROOT = os.environ.get("PATCHRIGHT_MCP_HOME") or os.path.expanduser("~/.patchright-browser")
CLI_PATH = os.environ.get(
    "PATCHRIGHT_MCP_CLI",
    "/workspaces/patchright-mcp/packages/playwright-mcp/cli.js",
)

Mode = Literal["headless", "headed"]
VALID_CAPS = ("vision", "pdf")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")


@dataclass
class Profile:
    """Rich profile definition. Persisted to profiles/<name>.json.

    Note: mode (headless/headed) is NOT part of the profile. Mode is a
    launch-time setting for a specific subprocess. The same profile can
    be opened in either mode (different subprocesses, different renders,
    but same cookies/storage via shared user-data-dir).
    """
    name: str
    description: str = ""
    caps: list[str] = field(default_factory=list)
    proxy: Optional[str | dict] = None
    userAgent: Optional[str] = None
    viewport: dict = field(default_factory=lambda: {"width": 1280, "height": 800})
    locale: str = "en-US"
    timezone: str = "Asia/Jakarta"
    fingerprint: dict = field(default_factory=lambda: {"hideWebDriver": True, "stealth": True})
    geo: Optional[dict] = None
    network: dict = field(default_factory=dict)
    downloads: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    # ---------- paths ----------
    def data_dir(self, root: str = ROOT) -> str:
        return os.path.join(root, "profiles", self.name)

    def config_path(self, root: str = ROOT) -> str:
        return os.path.join(root, "configs", f"{self.name}.json")

    def downloads_dir(self, root: str = ROOT) -> str:
        d = self.downloads or f"~/Downloads/patchright-mcp/{self.name}/"
        return os.path.expanduser(d)

    def to_dict(self) -> dict:
        return asdict(self)


def detect_gui() -> bool:
    """True if a usable X/Wayland display is available on this host.

    Order of checks (most reliable first):
    1. /tmp/.X11-unix/X* socket exists (most reliable X server indicator)
    2. Xorg process running with -seat (Debian/Ubuntu convention)
    3. DISPLAY env set + xdpyinfo can connect
    4. Wayland socket exists in XDG_RUNTIME_DIR
    """
    # 1) X11 socket files are the most direct indicator
    x11_unix = "/tmp/.X11-unix"
    if os.path.isdir(x11_unix):
        try:
            for entry in os.listdir(x11_unix):
                if entry.startswith("X"):
                    return True
        except OSError:
            pass

    # 2) Xorg process with -seat flag (Debian/Ubuntu/XFCE convention)
    if shutil.which("pgrep"):
        try:
            r = subprocess.run(
                ["pgrep", "-f", "Xorg.*-seat"],
                capture_output=True, text=True, timeout=2,
            )
            if r.returncode == 0 and r.stdout.strip():
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    # 3) DISPLAY env set and xdpyinfo can connect
    disp = os.environ.get("DISPLAY")
    if disp and shutil.which("xdpyinfo"):
        try:
            subprocess.run(
                ["xdpyinfo"], env={**os.environ, "DISPLAY": disp},
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=3,
            )
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    # 4) Wayland display available
    wayland = os.environ.get("WAYLAND_DISPLAY")
    if wayland:
        runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
        if os.path.isfile(os.path.join(runtime, wayland)):
            return True

    return False


def default_mode() -> str:
    """Default render mode when caller doesn't specify.

    Per requirement: if server has GUI, default is 'headed' (more capable,
    user can see browser). If no GUI, fall back to 'headless'.
    Caller can always override by passing mode='headed'|'headless' explicitly.
    """
    return "headed" if detect_gui() else "headless"

def validate_profile_spec(spec: dict) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errs: list[str] = []
    name = spec.get("name", "")
    if not name:
        errs.append("name is required")
    elif not SLUG_RE.match(name):
        errs.append(f"invalid name '{name}': must match {SLUG_RE.pattern}")
    for cap in spec.get("caps", []) or []:
        if cap not in VALID_CAPS:
            errs.append(f"unknown cap {cap!r}; valid: {VALID_CAPS}")
    proxy = spec.get("proxy")
    if proxy is not None:
        if isinstance(proxy, str):
            try:
                p = urlparse(proxy)
                if p.scheme not in ("http", "https", "socks5", "socks5h"):
                    errs.append(f"proxy scheme must be http/https/socks5, got {p.scheme!r}")
            except Exception as e:
                errs.append(f"invalid proxy URL: {e}")
        elif isinstance(proxy, dict):
            if "server" not in proxy:
                errs.append("proxy dict must have 'server' key")
            else:
                try:
                    p = urlparse(proxy["server"])
                    if p.scheme not in ("http", "https", "socks5", "socks5h"):
                        errs.append(f"proxy.server scheme must be http/https/socks5, got {p.scheme!r}")
                except Exception as e:
                    errs.append(f"invalid proxy.server URL: {e}")
            for k in ("username", "password", "bypass"):
                if k in proxy and not isinstance(proxy[k], str):
                    errs.append(f"proxy.{k} must be a string")
        else:
            errs.append("proxy must be a string (URL) or dict {server, username?, password?, bypass?}")
    vp = spec.get("viewport")
    if vp is not None:
        if not isinstance(vp, dict) or "width" not in vp or "height" not in vp:
            errs.append("viewport must be {width, height}")
        elif not (isinstance(vp["width"], int) and vp["width"] > 0):
            errs.append("viewport.width must be positive int")
        elif not (isinstance(vp["height"], int) and vp["height"] > 0):
            errs.append("viewport.height must be positive int")
    geo = spec.get("geo")
    if geo is not None:
        if not isinstance(geo, dict) or "lat" not in geo or "lon" not in geo:
            errs.append("geo must be {lat, lon, [accuracy]}")
    return errs


def to_patchright_config(profile: Profile, mode: Mode = "headless") -> dict:
    """Convert Profile → patchright-mcp config JSON (consumed by --config).

    `mode` is passed in (not stored on profile) so the same profile can
    launch in either headless or headed mode.

    Only emits non-default fields to keep the config small.
    """
    launch_opts: dict = {
        "executablePath": "/usr/bin/chromium",
        "headless": mode == "headless",
        "args": ["--disable-infobars"],
    }
    if profile.proxy:
        # proxy may be a string (URL) or dict {server, username?, password?, bypass?}
        # Chromium's --proxy-server accepts ONLY host:port (NO credentials in URL).
        # Credentials must be injected via CDP after browser launch.
        from urllib.parse import urlparse
        if isinstance(profile.proxy, str):
            p = urlparse(profile.proxy)
            host = p.hostname or "127.0.0.1"
            port = p.port or (1080 if p.scheme.startswith("socks") else 8080)
            scheme = p.scheme or "http"
            launch_opts["args"].append(f"--proxy-server={scheme}://{host}:{port}")
            if p.username:
                launch_opts["_proxy_auth"] = {
                    "username": p.username,
                    "password": p.password or "",
                }
        elif isinstance(profile.proxy, dict):
            server = profile.proxy.get("server", "")
            username = profile.proxy.get("username", "")
            password = profile.proxy.get("password", "")
            p = urlparse(server)
            host = p.hostname or "127.0.0.1"
            port = p.port or (1080 if p.scheme.startswith("socks") else 8080)
            scheme = p.scheme or "http"
            launch_opts["args"].append(f"--proxy-server={scheme}://{host}:{port}")
            if username:
                launch_opts["_proxy_auth"] = {
                    "username": username,
                    "password": password,
                }
            bypass = profile.proxy.get("bypass")
            if bypass:
                launch_opts["args"].append(f"--proxy-bypass-list={bypass}")

    ctx_opts: dict = {}
    if profile.userAgent:
        ctx_opts["userAgent"] = profile.userAgent
    if profile.viewport:
        ctx_opts["viewport"] = profile.viewport
    if profile.locale and profile.locale != "en-US":
        ctx_opts["locale"] = profile.locale
    if profile.timezone and profile.timezone != "Asia/Jakarta":
        ctx_opts["timezoneId"] = profile.timezone
    if profile.geo:
        ctx_opts["geolocation"] = {
            "latitude": profile.geo.get("lat"),
            "longitude": profile.geo.get("lon"),
            "accuracy": profile.geo.get("accuracy", 50),
        }
        ctx_opts["permissions"] = ["geolocation"]

    network_cfg: dict = {}
    if profile.network:
        if profile.network.get("allowedOrigins"):
            network_cfg["allowedOrigins"] = profile.network["allowedOrigins"]
        if profile.network.get("blockedOrigins"):
            network_cfg["blockedOrigins"] = profile.network["blockedOrigins"]

    config: dict = {
        "browser": {
            "browserName": "chromium",
            "launchOptions": launch_opts,
        },
        "capabilities": list(profile.caps),
    }
    if ctx_opts:
        config["browser"]["contextOptions"] = ctx_opts
    if network_cfg:
        config["network"] = network_cfg

    return config


def profile_from_dict(spec: dict) -> Profile:
    """Build Profile from persisted JSON dict. Validates."""
    errs = validate_profile_spec(spec)
    if errs:
        raise ValueError("invalid profile spec: " + "; ".join(errs))
    return Profile(
        name=spec["name"],
        description=spec.get("description", ""),
        caps=list(spec.get("caps", []) or []),
        proxy=spec.get("proxy"),
        userAgent=spec.get("userAgent"),
        viewport=spec.get("viewport") or {"width": 1280, "height": 800},
        locale=spec.get("locale", "en-US"),
        timezone=spec.get("timezone", "Asia/Jakarta"),
        fingerprint=spec.get("fingerprint") or {"hideWebDriver": True, "stealth": True},
        geo=spec.get("geo"),
        network=spec.get("network") or {},
        downloads=spec.get("downloads"),
        tags=list(spec.get("tags", []) or []),
    )


if __name__ == "__main__":
    # Quick smoke test
    import json
    p = Profile(name="test", caps=["vision"], viewport={"width": 1280, "height": 800})
    cfg = to_patchright_config(p, mode="headed")
    print(json.dumps(cfg, indent=2))
    print(f"\ngui_detected: {detect_gui()}")
    print(f"\nerrors: {validate_profile_spec({'name': 'foo bar'})}")
