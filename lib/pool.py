"""Subprocess pool for patchright-mcp-bridge.

We let mcp.client.stdio.stdio_client own the subprocess lifecycle.
We just track session + cm so we can close them later.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional

import json

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from profile_schema import CLI_PATH, ROOT, Profile, detect_gui, to_patchright_config

log = logging.getLogger(__name__)

_STDERR_DIR = os.path.join(ROOT, "logs")


@dataclass
class ProfileProcess:
    """One live patchright-mcp subprocess for one profile.

    Same Profile can be spawned multiple times in different modes.
    """
    name: str
    mode: str  # "headless" | "headed"
    profile: Profile
    config_path: str  # path to the config JSON we wrote for this spawn
    streams_cm: object                # AsyncContextManager from stdio_client
    read_stream: object
    write_stream: object
    session: ClientSession
    started_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    last_error: Optional[str] = None
    clean_shutdown: bool = False

    def touch(self) -> None:
        self.last_used_at = time.time()

    def uptime(self) -> float:
        return time.time() - self.started_at

    async def call(self, tool: str, arguments: dict, timeout: float = 60.0) -> dict:
        """Forward a tool call to this subprocess via MCP."""
        self.touch()
        try:
            result = await asyncio.wait_for(
                self.session.call_tool(tool, arguments=arguments),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            self.last_error = f"timeout after {timeout}s calling {tool}"
            raise
        return _result_to_dict(result)

    def is_alive(self) -> bool:
        return self.session is not None


class ProfilePool:
    """Pool of ProfileProcess keyed by (profile_name, mode)."""

    def __init__(self) -> None:
        self._procs: dict[tuple[str, str], ProfileProcess] = {}
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def acquire(self, name: str, profile: Profile, mode: Optional[str] = None) -> ProfileProcess:
        """Get or spawn the subprocess for this profile+mode. Serialized per-key.

        mode: "headless" | "headed". If None, auto-detect from GUI.
        Same profile can have multiple subprocesses (one per mode).
        """
        if mode is None:
            mode = default_mode()
        key = (name, mode)
        async with self._global_lock:
            lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            existing = self._procs.get(key)
            if existing and existing.is_alive() and not existing.last_error:
                existing.touch()
                return existing
            proc = await self._spawn(profile, mode)
            self._procs[key] = proc
            return proc

    async def _spawn(self, profile: Profile, mode: str) -> ProfileProcess:
        os.makedirs(_STDERR_DIR, exist_ok=True)

        # Safety: kill any orphan chromium using this user-data-dir
        user_data = profile.data_dir(ROOT)
        try:
            result = subprocess.run(
                ["pgrep", "-f", f"chromium.*{user_data}"],
                capture_output=True, text=True, timeout=2,
            )
            for pid in result.stdout.strip().split():
                if pid.isdigit():
                    log.info(f"killing orphan chromium PID {pid} for {profile.name}")
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        await asyncio.sleep(1)  # grace period
                        os.kill(int(pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            # Wait for SingletonLock to be released
            lock = os.path.join(user_data, "SingletonLock")
            for _ in range(25):  # max 5s
                if not os.path.exists(lock):
                    break
                await asyncio.sleep(0.2)
        except Exception as e:
            log.warning(f"orphan chromium cleanup failed for {profile.name}: {e}")

        # Write a mode-specific config file (so multiple spawns of same profile
        # in different modes don't collide)
        config_path = os.path.join(ROOT, "configs", f"{profile.name}.{mode}.json")
        cfg = to_patchright_config(profile, mode=mode)
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        tmp_cfg = config_path + ".tmp"
        with open(tmp_cfg, "w") as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp_cfg, config_path)

        cmd = [
            CLI_PATH,
            "--user-data-dir", profile.data_dir(ROOT),
            "--config", config_path,
                    ]
        env = {**os.environ}
        if mode == "headed":
            env["DISPLAY"] = os.environ.get("DISPLAY") or ":0"
        params = StdioServerParameters(command=cmd[0], args=cmd[1:], env=env)

        streams_cm = stdio_client(params)
        try:
            read_stream, write_stream = await asyncio.wait_for(
                streams_cm.__aenter__(), timeout=15.0,
            )
            session = ClientSession(read_stream, write_stream)
            await asyncio.wait_for(session.__aenter__(), timeout=10.0)
            await asyncio.wait_for(session.initialize(), timeout=15.0)
        except Exception as e:
            try: await streams_cm.__aexit__(type(e), e, e.__traceback__)
            except Exception: pass
            raise RuntimeError(f"failed to spawn patchright-mcp for {profile.name} ({mode}): {e}")

        return ProfileProcess(
            name=profile.name,
            mode=mode,
            profile=profile,
            config_path=config_path,
            streams_cm=streams_cm,
            read_stream=read_stream,
            write_stream=write_stream,
            session=session,
        )

    async def close(self, name: str, mode: Optional[str] = None) -> bool:
        """Close subprocess(es) for a profile.

        If mode specified, close just that variant. Otherwise close all modes.
        """
        if mode is not None:
            key = (name, mode)
            async with self._global_lock:
                proc = self._procs.pop(key, None)
                self._locks.pop(key, None)
            if proc is None:
                return False
            return await self._terminate(proc)
        # Close all modes for this profile
        async with self._global_lock:
            keys = [k for k in self._procs if k[0] == name]
            procs = [self._procs.pop(k) for k in keys]
            for k in keys:
                self._locks.pop(k, None)
        any_alive = False
        for proc in procs:
            if await self._terminate(proc):
                any_alive = True
        return any_alive

    async def _terminate(self, proc: ProfileProcess) -> bool:
        """Gracefully shutdown: SIGTERM → wait 5s → SIGKILL if needed."""
        proc.clean_shutdown = True
        # 1. Close MCP session (patchright-mcp will shut down chromium)
        try:
            await proc.session.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            await proc.streams_cm.__aexit__(None, None, None)
        except Exception:
            pass
        # 2. Wait up to 5s for chromium to flush cookies
        import time
        deadline = time.time() + 5.0
        user_data = proc.profile.data_dir(ROOT)
        while time.time() < deadline:
            # Check if chromium still has lock on this data dir
            lock = os.path.join(user_data, "SingletonLock")
            if not os.path.exists(lock):
                break
            await asyncio.sleep(0.2)
        # 3. Force kill any orphan chromium on this data dir (last resort)
        try:
            result = subprocess.run(
                ["pgrep", "-f", f"chromium.*{user_data}"],
                capture_output=True, text=True, timeout=2,
            )
            for pid in result.stdout.strip().split():
                if pid.isdigit():
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        except Exception:
            pass
        return True

    async def close_all(self) -> None:
        async with self._global_lock:
            keys = list(self._procs.keys())
            procs = [self._procs.pop(k) for k in keys]
            self._locks.clear()
        for proc in procs:
            await self._terminate(proc)

    def alive_names(self) -> list[str]:
        return [f"{n}/{m}" for (n, m), p in self._procs.items() if p.is_alive()]

    def get(self, name: str, mode: Optional[str] = None) -> Optional[ProfileProcess]:
        """Get process for (name, mode). If mode None, returns first match."""
        if mode is not None:
            return self._procs.get((name, mode))
        for (n, m), p in self._procs.items():
            if n == name:
                return p
        return None

    def all(self) -> list[ProfileProcess]:
        return list(self._procs.values())

    async def evict_idle(self, idle_seconds: int, default_name: Optional[str]) -> list[str]:
        """Kill non-default profiles idle for >idle_seconds. Returns evicted names."""
        now = time.time()
        evicted: list[tuple[str, str]] = []
        for (name, mode), proc in list(self._procs.items()):
            if name == default_name:
                continue
            if now - proc.last_used_at > idle_seconds:
                await self.close(name, mode)
                evicted.append((name, mode))
        return [f"{n}/{m}" for n, m in evicted]


def _result_to_dict(result) -> dict:
    """Convert mcp CallToolResult → plain dict for JSON serialization."""
    out: dict = {"isError": getattr(result, "isError", False), "content": []}
    for item in getattr(result, "content", []) or []:
        try:
            t = getattr(item, "type", "unknown")
            if t == "text" or hasattr(item, "text"):
                out["content"].append({"type": "text", "text": getattr(item, "text", "")})
            else:
                # Image or other
                out["content"].append({"type": t, "raw": str(item)})
        except Exception:
            out["content"].append({"type": "error", "raw": str(item)})
    return out
