#!/usr/bin/env python3
"""patchright-mcp-bridge: HTTP API server exposing patchright with profile management.

Usage:
    patchright-bridge                   # start HTTP server on port 9877
    patchright-bridge --port 8080       # custom port
    patchright-bridge --probe           # debug: list tools, exit
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback
from typing import Any, Optional

# Ensure lib is importable when launched directly
_LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _LIB_DIR)
sys.path.insert(0, os.path.join(_LIB_DIR, "lib"))

from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import ImageContent, TextContent, Tool

from lib import logging_redact, pool as pool_mod, profile_schema, registry, proxy_registry

ROOT = os.environ.get("PATCHRIGHT_MCP_HOME") or os.path.expanduser("~/.patchright-browser")


# ---------- setup ----------

import logging as _logging

LOG = logging_redact.setup_logging(
    level=_logging.DEBUG if os.environ.get("PATCHRIGHT_BRIDGE_VERBOSE") == "1" else _logging.INFO
)
log = _logging.getLogger("patchright_bridge.main")


# ---------- bridge state ----------

class BridgeState:
    """Top-level state: pool + default profile + session memory.

    Mode (headless/headed) is per-spawn, not per-profile. session_mode
    tracks the last mode used in this session.
    """

    def __init__(self) -> None:
        self.pool = pool_mod.ProfilePool()
        self.default_profile: Optional[str] = None
        self.session_profile: Optional[str] = None  # last explicit profile
        self.session_mode: Optional[str] = None      # last explicit mode
        self._idle_task: Optional[asyncio.Task] = None

    def resolve_profile(self, explicit: Optional[str]) -> str:
        if explicit:
            self.session_profile = explicit
            return explicit
        if self.session_profile:
            return self.session_profile
        if self.default_profile:
            return self.default_profile
        raise ValueError("no profile specified and no default set; call profile_set_default first")

    def resolve_mode(self, explicit: Optional[str]) -> str:
        if explicit:
            self.session_mode = explicit
            return explicit
        if self.session_mode:
            return self.session_mode
        # Auto-detect
        return profile_schema.default_mode()

    async def start(self) -> None:
        """Initialize: load registry, spawn default profile subprocess (default mode)."""
        reg = registry.load_registry()
        self.default_profile = reg.get("default")
        if self.default_profile:
            try:
                prof = registry.get_profile(self.default_profile)
                if prof:
                    mode = self.resolve_mode(None)
                    log.info(f"auto-spawning default profile: {self.default_profile} (mode={mode})")
                    await self.pool.acquire(self.default_profile, prof, mode=mode)
            except Exception as e:
                log.warning(f"failed to spawn default profile: {e}")
        idle_seconds = int(os.environ.get("IDLE_TIMEOUT_SECONDS", "3600"))
        self._idle_task = asyncio.create_task(self._idle_sweeper(idle_seconds))

    async def shutdown(self) -> None:
        log.info("bridge shutting down")
        # Remove PID file
        pid_path = os.path.join(ROOT, ".bridge.pid")
        try:
            if os.path.exists(pid_path):
                with open(pid_path) as f:
                    pid = int(f.read().strip())
                if pid == os.getpid():
                    os.remove(pid_path)
        except Exception:
            pass
        if self._idle_task:
            self._idle_task.cancel()
            try: await self._idle_task
            except Exception: pass
        await self.pool.close_all()

    async def _idle_sweeper(self, idle_seconds: int) -> None:
        log.info(f"idle sweeper running, threshold={idle_seconds}s")
        while True:
            try:
                await asyncio.sleep(60)
                evicted = await self.pool.evict_idle(idle_seconds, self.default_profile)
                if evicted:
                    log.info(f"evicted idle profiles: {evicted}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"idle sweeper error: {e}")


# ---------- tool implementations ----------

def _result_text(text: str) -> list[TextContent]:
    return [TextContent(type="text", text=text)]


def _result_json(obj: Any) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(obj, indent=2, default=str))]


def _err(msg: str) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps({"error": msg}, indent=2))]


# ---------- main server ----------

async def serve(port: int = 9877, host: str = "127.0.0.1") -> None:
    """Run as persistent HTTP server (StreamableHTTP MCP)."""
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route
    from starlette.responses import JSONResponse

    server: Server = Server("patchright-bridge")
    state = BridgeState()

    # ----- list_tools -----
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools: list[Tool] = []
        tools.extend(_profile_tools())
        try:
            if state.default_profile:
                prof = registry.get_profile(state.default_profile)
                if prof:
                    mode = state.resolve_mode(None)
                    proc = await state.pool.acquire(state.default_profile, prof, mode=mode)
                    upstream = await proc.session.list_tools()
                    for t in upstream.tools:
                        if t.name in ("browser_console_messages",
                                      "browser_network_requests",
                                      "browser_take_screenshot"):
                            continue
                        wrapped = _wrap_tool_with_profile(t)
                        if wrapped:
                            tools.append(wrapped)
        except Exception as e:
            log.warning(f"could not load upstream tools: {e}")
        tools.extend(_custom_tools())
        log.debug(f"total tools exposed: {len(tools)}")
        return tools

    # ----- call_tool -----
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        log.info(f"tool call: {name} args_keys={list(arguments.keys())}")
        try:
            return await _dispatch(state, name, arguments or {})
        except Exception as e:
            log.error(f"tool {name} failed: {e}\n{traceback.format_exc()}")
            return _err(f"{type(e).__name__}: {e}")

    # Startup
    await state.start()

    # StreamableHTTP transport
    from mcp.server.fastmcp.server import StreamableHTTPASGIApp
    from contextlib import asynccontextmanager

    session_manager = StreamableHTTPSessionManager(app=server, stateless=False)
    http_app = StreamableHTTPASGIApp(session_manager)

    async def health(request):
        profiles = registry.list_profiles()
        return JSONResponse({
            "status": "ok",
            "default_profile": state.default_profile,
            "profiles": len(profiles.get("profiles", [])),
            "pool_size": len(list(state.pool.all())),
        })

    @asynccontextmanager
    async def lifespan(app):
        async with session_manager.run():
            yield
        await state.shutdown()

    app = Starlette(
        routes=[
            Route("/health", health),
            Mount("/mcp/", app=http_app),
        ],
        lifespan=lifespan,
    )

    log.info(f"bridge ready on http://{host}:{port}/mcp/")

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    srv = uvicorn.Server(config)
    await srv.serve()

    await state.shutdown()


# ---------- tool definitions ----------

def _profile_tools() -> list[Tool]:
    """8 profile_* tools. Schemas inline."""
    return [
        Tool(name="profile_list", description="List all registered profiles with status.",
             inputSchema={"type": "object", "properties": {}}),
        Tool(name="profile_create", description="Create a new profile. Does NOT spawn subprocess. Mode is per-spawn (set in profile_open).",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string", "description": "Profile name (slug, lowercase, unique)"},
                 "description": {"type": "string", "default": ""},
                 "caps": {"type": "array", "items": {"type": "string", "enum": ["vision", "pdf"]}, "default": []},
                 "proxy": {
                     "description": "Proxy config. String: URL like 'socks5://user:pass@host:port'. Dict: {server, username?, password?, bypass?}",
                     "oneOf": [
                         {"type": "string"},
                         {"type": "object", "properties": {
                             "server": {"type": "string"},
                             "username": {"type": "string"},
                             "password": {"type": "string"},
                             "bypass": {"type": "string", "description": "Comma-separated bypass list"}
                         }, "required": ["server"]}
                     ]
                 },
                 "userAgent": {"type": "string"},
                 "viewport": {"type": "object"},
                 "locale": {"type": "string", "default": "en-US"},
                 "timezone": {"type": "string", "default": "Asia/Jakarta"},
                 "fingerprint": {"type": "object"},
                 "geo": {"type": "object"},
                 "network": {"type": "object"},
                 "downloads": {"type": "string"},
                 "tags": {"type": "array", "items": {"type": "string"}},
             }, "required": ["name"]}),
        Tool(name="profile_delete", description="Remove profile entirely (data + config + registry).",
             inputSchema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}),
        Tool(name="profile_open", description="Spawn subprocess for profile (lazy). Mode is per-spawn — same profile can have multiple subprocesses (one per mode).",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string"},
                 "mode": {"type": "string", "enum": ["headless", "headed"], "description": "Render mode (default = auto-detect or session memory)"},
             }, "required": ["name"]}),
        Tool(name="profile_close", description="Kill subprocess but keep data dir. If mode given, close just that variant.",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string"},
                 "mode": {"type": "string", "enum": ["headless", "headed"]},
             }, "required": ["name"]}),
        Tool(name="profile_set_default", description="Mark profile as default. Always alive.",
             inputSchema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}),
        Tool(name="profile_update", description="Update existing profile fields (proxy, caps, viewport, etc). Kills live subprocess.",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string"},
                 "description": {"type": "string"},
                 "caps": {"type": "array", "items": {"type": "string", "enum": ["vision", "pdf"]}},
                 "proxy": {
                     "description": "Replace proxy config. Use null to remove.",
                     "oneOf": [
                         {"type": "string"},
                         {"type": "object", "properties": {
                             "server": {"type": "string"},
                             "username": {"type": "string"},
                             "password": {"type": "string"},
                             "bypass": {"type": "string"}
                         }, "required": ["server"]},
                         {"type": "null"}
                     ]
                 },
                 "userAgent": {"type": "string"},
                 "viewport": {"type": "object"},
                 "locale": {"type": "string"},
                 "timezone": {"type": "string"},
                 "fingerprint": {"type": "object"},
                 "geo": {"type": "object"},
                 "network": {"type": "object"},
                 "downloads": {"type": "string"},
                 "tags": {"type": "array", "items": {"type": "string"}},
             }, "required": ["name"]}),
        Tool(name="profile_rename", description="Rename profile (move data dir).",
             inputSchema={"type": "object", "properties": {
                 "old": {"type": "string"}, "new": {"type": "string"},
             }, "required": ["old", "new"]}),
        Tool(name="profile_inspect", description="Deep state: alive, browser state, storage, fingerprint.",
             inputSchema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}),
    ]


def _wrap_tool_with_profile(upstream_tool: Tool) -> Optional[Tool]:
    """Add optional profile + mode args to upstream patchright tool schema."""
    if upstream_tool.name.startswith("profile_"):
        return None
    schema = dict(upstream_tool.inputSchema or {})
    schema.setdefault("type", "object")
    props = dict(schema.get("properties", {}))
    if "profile" not in props:
        props["profile"] = {
            "type": "string",
            "description": "Profile name. Default = persistent default or session memory.",
            "default": None,
        }
    if "mode" not in props:
        props["mode"] = {
            "type": "string",
            "enum": ["headless", "headed"],
            "description": "Render mode. Default = auto-detect (headed if GUI, else headless).",
            "default": None,
        }
    schema["properties"] = props
    desc = (upstream_tool.description or "") + " [profile+mode params select browser context]"
    return Tool(name=upstream_tool.name, description=desc, inputSchema=schema)


def _custom_tools() -> list[Tool]:
    """Cookies (4), clipboard (2), health (1), console/network/screenshot (3)."""
    profile_arg = {
        "type": "string",
        "description": "Profile name (default if omitted)",
        "default": None,
    }
    mode_arg = {
        "type": "string",
        "enum": ["headless", "headed"],
        "description": "Render mode (default = auto-detect or session memory)",
        "default": None,
    }
    return [
        # Override upstream tools that have schema defaults patchright-mcp ignores.
        # Custom schemas with proper JSON-Schema "default" fields so MCP clients
        # (Hermes) accept requests without these optional params.
        Tool(name="browser_console_messages",
             description="Returns all console messages. Level defaults to 'info'.",
             inputSchema={"type": "object", "properties": {
                 "level": {"type": "string", "enum": ["error", "warning", "info", "debug"],
                           "default": "info"},
                 "filename": {"type": "string"},
                 "profile": profile_arg, "mode": mode_arg,
             }}),
        Tool(name="browser_network_requests",
             description="Returns all network requests. includeStatic defaults to false.",
             inputSchema={"type": "object", "properties": {
                 "includeStatic": {"type": "boolean", "default": False},
                 "filename": {"type": "string"},
                 "profile": profile_arg, "mode": mode_arg,
             }}),
        Tool(name="browser_take_screenshot",
             description="Take a screenshot. Type defaults to png. Returns image content.",
             inputSchema={"type": "object", "properties": {
                 "type": {"type": "string", "enum": ["png", "jpeg"], "default": "png"},
                 "filename": {"type": "string"},
                 "fullPage": {"type": "boolean", "default": False},
                 "profile": profile_arg, "mode": mode_arg,
             }}),
        # Cookies / clipboard / health (unchanged)
        Tool(name="browser_health", description="Quick health check: alive, current URL, tab count.",
             inputSchema={"type": "object", "properties": {"profile": profile_arg, "mode": mode_arg}}),
        Tool(name="browser_cookies_list", description="List all cookies in current browser context.",
             inputSchema={"type": "object", "properties": {"profile": profile_arg, "mode": mode_arg}}),
        Tool(name="browser_cookies_get", description="Get single cookie by name.",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string"}, "profile": profile_arg, "mode": mode_arg,
             }, "required": ["name"]}),
        Tool(name="browser_cookies_set", description="Set cookie value.",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string"}, "value": {"type": "string"},
                 "domain": {"type": "string"}, "path": {"type": "string", "default": "/"},
                 "expires": {"type": "number", "description": "Unix timestamp, -1 for session"},
                 "httpOnly": {"type": "boolean", "default": False},
                 "secure": {"type": "boolean", "default": False},
                 "sameSite": {"type": "string", "enum": ["Strict", "Lax", "None"], "default": "Lax"},
                 "profile": profile_arg, "mode": mode_arg,
             }, "required": ["name", "value"]}),
        Tool(name="browser_cookies_delete", description="Delete cookies matching name+domain+path.",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string"}, "domain": {"type": "string"},
                 "path": {"type": "string", "default": "/"},
                 "profile": profile_arg, "mode": mode_arg,
             }, "required": ["name"]}),
        Tool(name="browser_clipboard_read", description="Read text from clipboard (requires clipboard-read permission, auto-granted).",
             inputSchema={"type": "object", "properties": {"profile": profile_arg, "mode": mode_arg}}),
        Tool(name="browser_clipboard_write", description="Write text to clipboard.",
             inputSchema={"type": "object", "properties": {
                 "text": {"type": "string"}, "profile": profile_arg, "mode": mode_arg,
             }, "required": ["text"]}),
        # Proxy management
        Tool(name="proxy_list", description="List all configured proxies.",
             inputSchema={"type": "object", "properties": {}}),
        Tool(name="proxy_add", description="Add or update a proxy configuration.",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string", "description": "Proxy name (unique)"},
                 "server": {"type": "string", "description": "Proxy server (host:port or URL)"},
                 "username": {"type": "string", "description": "Proxy username"},
                 "password": {"type": "string", "description": "Proxy password"},
                 "scheme": {"type": "string", "enum": ["http", "https", "socks5", "socks5h"], "default": "http"},
                 "bypass": {"type": "string", "description": "Comma-separated bypass list"},
                 "description": {"type": "string", "description": "Human-readable description"},
             }, "required": ["name", "server"]}),
        Tool(name="proxy_get", description="Get proxy details by name.",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string"},
             }, "required": ["name"]}),
        Tool(name="proxy_delete", description="Delete a proxy configuration.",
             inputSchema={"type": "object", "properties": {
                 "name": {"type": "string"},
             }, "required": ["name"]}),
    ]


# ---------- dispatcher ----------

async def _dispatch(state: BridgeState, name: str, args: dict) -> list[TextContent]:
    # Profile management
    if name == "profile_list":
        return _result_json(_profile_list(state))
    if name == "profile_create":
        return _result_json(await _profile_create(state, args))
    if name == "profile_delete":
        return _result_json(await _profile_delete(state, args))
    if name == "profile_open":
        return _result_json(await _profile_open(state, args))
    if name == "profile_close":
        return _result_json(await _profile_close(state, args))
    if name == "profile_set_default":
        return _result_json(await _profile_set_default(state, args))
    if name == "profile_update":
        return _result_json(await _profile_update(state, args))
    if name == "profile_rename":
        return _result_json(await _profile_rename(state, args))
    if name == "profile_inspect":
        return _result_json(await _profile_inspect(state, args))
    # Cookies + clipboard + health
    if name == "browser_health":
        return _result_json(await _browser_health(state, args))
    if name in ("browser_cookies_list", "browser_cookies_get", "browser_cookies_set", "browser_cookies_delete"):
        return _result_json(await _browser_cookies(state, name, args))
    if name in ("browser_clipboard_read", "browser_clipboard_write"):
        return _result_json(await _browser_clipboard(state, name, args))
    # Proxy management
    if name == "proxy_list":
        return _result_json(_proxy_list())
    if name == "proxy_add":
        return _result_json(_proxy_add(args))
    if name == "proxy_get":
        return _result_json(_proxy_get(args))
    if name == "proxy_delete":
        return _result_json(_proxy_delete(args))
    # Browser control (patchright upstream) — includes console, network, etc.
    return await _dispatch_browser(state, name, args)


# ---------- profile action handlers ----------

def _profile_list(state: BridgeState) -> dict:
    listing = registry.list_profiles()
    # Enrich with live status (which mode variants are alive)
    for p in listing["profiles"]:
        procs = [proc for proc in state.pool.all() if proc.name == p["name"]]
        p["alive"] = len(procs) > 0
        p["alive_modes"] = [proc.mode for proc in procs]
        p["pid"] = None  # stdio_client doesn't expose PID
        p["last_used_at"] = max((proc.last_used_at for proc in procs), default=None)
        p["uptime_seconds"] = max((proc.uptime() for proc in procs), default=0)
        p["is_default"] = (p["name"] == listing["default"])
    return listing


async def _profile_create(state: BridgeState, args: dict) -> dict:
    spec = dict(args)
    spec.pop("mode", None)  # mode not stored on profile (per-spawn only)
    # Merge with defaults if key fields absent (so empty spec still produces
    # a usable profile with sensible viewport/locale/etc)
    defaults = {
        "viewport": {"width": 1280, "height": 800},
        "locale": "en-US",
        "timezone": "Asia/Jakarta",
        "fingerprint": {"hideWebDriver": True, "stealth": True},
        "network": {},
        "tags": [],
    }
    for k, v in defaults.items():
        if k not in spec or spec[k] is None:
            spec[k] = v
    if "caps" not in spec:
        spec["caps"] = []
    profile = registry.create_profile(spec)
    return {
        "name": profile.name,
        "data_dir": profile.data_dir(),
        "config_path": profile.config_path(),
        "spawned_now": False,
        "caps": profile.caps,
        "note": "mode is per-spawn — use profile_open with mode= to launch",
    }


async def _profile_delete(state: BridgeState, args: dict) -> dict:
    name = args["name"]
    # Kill all subprocesses for this profile (any mode)
    await state.pool.close(name)
    registry.delete_profile(name)
    # If this was default, update state
    if state.default_profile == name:
        reg = registry.load_registry()
        state.default_profile = reg.get("default")
    return {"name": name, "deleted": True, "new_default": state.default_profile}


async def _profile_close(state: BridgeState, args: dict) -> dict:
    name = args["name"]
    mode = args.get("mode")  # optional; close just one mode if specified
    was_alive = await state.pool.close(name, mode=mode)
    return {"name": name, "alive": False, "was_alive": was_alive, "mode": mode}


async def _profile_open(state: BridgeState, args: dict) -> dict:
    name = args["name"]
    mode = state.resolve_mode(args.get("mode"))
    prof = registry.get_profile(name)
    if not prof:
        raise ValueError(f"profile not found: {name}")
    t0 = time.time()
    proc = await state.pool.acquire(name, prof, mode=mode)
    tools_count = len((await proc.session.list_tools()).tools)
    return {
        "name": name,
        "mode": mode,
        "alive": True,
        "tools_count": tools_count,
        "spawn_duration_ms": int((time.time() - t0) * 1000),
    }


async def _profile_set_default(state: BridgeState, args: dict) -> dict:
    name = args["name"]
    prof = registry.get_profile(name)
    if not prof:
        raise ValueError(f"profile not found: {name}")
    registry.set_default(name)
    state.default_profile = name
    # Spawn it if not alive (default is always-alive). Use default mode.
    mode = state.resolve_mode(None)
    proc = await state.pool.acquire(name, prof, mode=mode)
    return {"name": name, "default": name, "alive": True, "mode": mode}


async def _profile_update(state: BridgeState, args: dict) -> dict:
    name = args["name"]
    updates = {k: v for k, v in args.items() if k != "name"}
    if not updates:
        raise ValueError("at least one update field required (besides 'name')")
    # Kill any live subprocesses — config may need re-write per spawn
    await state.pool.close(name)
    profile = registry.update_profile(name, updates)
    return {
        "name": profile.name,
        "updated_fields": list(updates.keys()),
        "data_dir": profile.data_dir(),
        "config_path": profile.config_path(),
        "spawned_now": False,
        "note": "live subprocess killed (if any). Spawn again with profile_open.",
    }


async def _profile_rename(state: BridgeState, args: dict) -> dict:
    old, new = args["old"], args["new"]
    await state.pool.close(old)  # all modes
    registry.rename_profile(old, new)
    if state.default_profile == old:
        registry.set_default(new)
        state.default_profile = new
    return {"old": old, "new": new, "alive": False}


async def _profile_inspect(state: BridgeState, args: dict) -> dict:
    name = args["name"]
    prof = registry.get_profile(name)
    if not prof:
        raise ValueError(f"profile not found: {name}")
    # Find any live process for this profile (any mode)
    proc = state.pool.get(name)
    info = {
        "name": name,
        "alive": proc is not None,
        "mode": proc.mode if proc else None,
        "caps": prof.caps,
        "fingerprint": {
            "user_agent": prof.userAgent or "(default Chromium UA)",
            "viewport": prof.viewport,
            "locale": prof.locale,
            "timezone": prof.timezone,
            "geolocation": prof.geo,
        },
        "network": prof.network,
        "data_dir": prof.data_dir(),
        "data_dir_bytes": _dir_size(prof.data_dir()),
        "config_path": prof.config_path(),
        "last_error": proc.last_error if proc else None,
    }
    if proc:
        info["uptime_seconds"] = proc.uptime()
        info["last_used_at"] = proc.last_used_at
        try:
            tabs_result = await proc.call("browser_tabs", {"action": "list"}, timeout=10)
            tabs_data = json.loads(tabs_result["content"][0]["text"]) if tabs_result.get("content") else {}
            info["browser"] = {
                "tab_count": len(tabs_data.get("tabs", [])) if isinstance(tabs_data, dict) else 0,
                "tabs_raw": str(tabs_data)[:500],
            }
        except Exception as e:
            info["browser"] = {"error": str(e)}
    return info


def _dir_size(path: str) -> int:
    total = 0
    try:
        for root, _, files in os.walk(path):
            for f in files:
                try: total += os.path.getsize(os.path.join(root, f))
                except OSError: pass
    except OSError: pass
    return total


# ---------- cookies / clipboard / health ----------

async def _browser_health(state: BridgeState, args: dict) -> dict:
    profile = state.resolve_profile(args.get("profile"))
    mode = state.resolve_mode(args.get("mode"))
    prof = registry.get_profile(profile)
    proc = await state.pool.acquire(profile, prof, mode=mode)
    tabs = await proc.call("browser_tabs", {"action": "list"}, timeout=10)
    return {
        "profile": profile,
        "mode": mode,
        "alive": True,
        "tab_count": len(tabs.get("content", [])),
        "last_error": proc.last_error,
    }


async def _browser_cookies(state: BridgeState, name: str, args: dict) -> dict:
    profile = state.resolve_profile(args.get("profile"))
    mode = state.resolve_mode(args.get("mode"))
    prof = registry.get_profile(profile)
    proc = await state.pool.acquire(profile, prof, mode=mode)
    # Use browser_evaluate with document.cookie for browser-side access.
    # page.context().cookies() is a Playwright server-side API and cannot
    # be called via browser_run_code (browser-side JS context).
    if name == "browser_cookies_list":
        code = "() => document.cookie.split('; ').filter(Boolean).map(c => { const i = c.indexOf('='); return {name: c.substring(0, i), value: c.substring(i+1)}; })"
        result = await proc.call("browser_evaluate", {"function": code}, timeout=15)
        return {"profile": profile, "result": result}
    if name == "browser_cookies_get":
        cname = args["name"]
        code = f"() => document.cookie.split('; ').filter(Boolean).find(c => c.startsWith({cname!r} + '='))"
        result = await proc.call("browser_evaluate", {"function": code}, timeout=15)
        return {"profile": profile, "result": result}
    if name == "browser_cookies_set":
        cookie = f"{args['name']}={args['value']}"
        code = f"() => {{ document.cookie = {cookie!r}; return document.cookie; }}"
        result = await proc.call("browser_evaluate", {"function": code}, timeout=15)
        return {"profile": profile, "result": result}
    if name == "browser_cookies_delete":
        cname = args["name"]
        code = f"() => {{ document.cookie = {cname!r} + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT'; return document.cookie; }}"
        result = await proc.call("browser_evaluate", {"function": code}, timeout=15)
        return {"profile": profile, "result": result}
    raise ValueError(f"unknown cookies tool: {name}")


async def _browser_clipboard(state: BridgeState, name: str, args: dict) -> dict:
    profile = state.resolve_profile(args.get("profile"))
    mode = state.resolve_mode(args.get("mode"))
    prof = registry.get_profile(profile)
    proc = await state.pool.acquire(profile, prof, mode=mode)
    if name == "browser_clipboard_read":
        code = "() => navigator.clipboard.readText().then(t => t).catch(e => ({error: e.message}))"
        result = await proc.call("browser_evaluate", {"function": code}, timeout=10)
        return {"profile": profile, "result": result}
    if name == "browser_clipboard_write":
        text = args["text"]
        code = f"() => navigator.clipboard.writeText({json.dumps(text)}).then(() => ({{success:true}})).catch(e => ({{error: e.message}}))"
        result = await proc.call("browser_evaluate", {"function": code}, timeout=10)
        return {"profile": profile, "result": result}
    raise ValueError(f"unknown clipboard tool: {name}")


# ---------- proxy management ----------

def _proxy_list() -> dict:
    """List all configured proxies."""
    proxies = proxy_registry.list_proxies()
    return {"proxies": proxies, "count": len(proxies)}


def _proxy_add(args: dict) -> dict:
    """Add or update a proxy configuration."""
    name = args.get("name")
    server = args.get("server")
    if not name or not server:
        raise ValueError("name and server are required")
    
    proxy = proxy_registry.add_proxy(
        name=name,
        server=server,
        username=args.get("username", ""),
        password=args.get("password", ""),
        scheme=args.get("scheme", "http"),
        bypass=args.get("bypass", ""),
        description=args.get("description", ""),
    )
    return {"name": proxy.name, "server": proxy.server, "description": proxy.description}


def _proxy_get(args: dict) -> dict:
    """Get proxy details by name."""
    name = args.get("name")
    if not name:
        raise ValueError("name is required")
    
    proxy = proxy_registry.get_proxy(name)
    if not proxy:
        raise ValueError(f"proxy not found: {name}")
    
    return {"name": proxy.name, "server": proxy.server, "scheme": proxy.scheme,
            "description": proxy.description, "has_auth": bool(proxy.username)}


def _proxy_delete(args: dict) -> dict:
    """Delete a proxy configuration."""
    name = args.get("name")
    if not name:
        raise ValueError("name is required")
    
    deleted = proxy_registry.delete_proxy(name)
    if not deleted:
        raise ValueError(f"proxy not found: {name}")
    
    return {"deleted": True, "name": name}


# ---------- browser control (forward to patchright subprocess) ----------

async def _dispatch_browser(state: BridgeState, name: str, args: dict) -> list[TextContent]:
    """Forward to underlying patchright-mcp subprocess, with profile + mode resolution."""
    profile = state.resolve_profile(args.pop("profile", None))
    mode = state.resolve_mode(args.pop("mode", None))
    # Workaround for patchright-mcp strict validation that ignores schema defaults.
    # Patchright's compiled schema uses .default("info") but runtime validator
    # marks the field as required regardless. Always inject defaults.
    _ALWAYS_DEFAULTS = {
        "browser_console_messages": {"level": "info"},
        "browser_network_requests": {"includeStatic": False},
        "browser_take_screenshot": {"type": "png"},
        "browser_resize": {},  # no defaults, but ensure dict shape
        "browser_navigate": {},  # see URL validation below
    }
    if name in _ALWAYS_DEFAULTS:
        for k, v in _ALWAYS_DEFAULTS[name].items():
            if args.get(k) is None:  # covers missing AND explicit null
                args[k] = v
    # Required params that patchright-mcp doesn't validate
    if name == "browser_navigate" and not args.get("url"):
        raise ValueError("browser_navigate requires 'url' argument")
    prof = registry.get_profile(profile)
    if not prof:
        raise ValueError(f"profile not found: {profile}")
    proc = await state.pool.acquire(profile, prof, mode=mode)
    log.info(f"forwarding {name} to profile {profile} (mode={mode})")
    result = await proc.call(name, args, timeout=120)
    return _result_json(result)


# ---------- entry point ----------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="patchright-mcp HTTP bridge")
    parser.add_argument("--port", type=int, default=9877)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--probe", action="store_true", help="Debug: list tools, exit")
    args = parser.parse_args()

    if args.probe:
        print(json.dumps({
            "registry": registry.list_profiles(),
            "env": {k: v for k, v in os.environ.items() if k.startswith("PATCHRIGHT_") or k == "DISPLAY" or k == "IDLE_TIMEOUT_SECONDS"},
        }, indent=2, default=str))
        sys.exit(0)

    asyncio.run(serve(port=args.port, host=args.host))
