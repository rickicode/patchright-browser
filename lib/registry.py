"""Persistent registry for patchright-mcp-bridge profiles.

File: ~/.patchright-mcp/profiles.json
Schema:
{
  "version": 1,
  "default": "rickicode",
  "profiles": {
    "<name>": {"path": "profiles/<name>.json"}
  }
}

Each profile's rich spec lives at profiles/<name>.json.

Concurrency: flock on ~/.patchright-mcp/.registry.lock for safe
concurrent access between bridge and CLI.
"""
from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from typing import Iterator, Optional

from profile_schema import (
    Profile,
    ROOT,
    profile_from_dict,
    to_patchright_config,
    validate_profile_spec,
)
# Alias to avoid name shadowing in create_profile
import profile_schema as profile_schema_module

REGISTRY_VERSION = 1


def _lock_path(root: str = ROOT) -> str:
    return os.path.join(root, ".registry.lock")


def _registry_path(root: str = ROOT) -> str:
    return os.path.join(root, "profiles.json")


def _atomic_write_json(path: str, data: dict) -> None:
    """Write JSON atomically: tmp file + fsync + os.replace."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=os.path.dirname(path),
        prefix=".tmp-",
        suffix=os.path.splitext(path)[1] or ".json",
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
        raise


@contextmanager
def registry_lock(root: str = ROOT, timeout: float = 5.0) -> Iterator[None]:
    """Exclusive flock on registry. Raises TimeoutError if can't acquire in time."""
    os.makedirs(root, exist_ok=True)
    lock_path = _lock_path(root)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        # Poll-based blocking lock with timeout
        import time
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"could not acquire registry lock in {timeout}s")
                time.sleep(0.05)
        yield
    finally:
        try: fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError: pass
        os.close(fd)


def _empty_registry() -> dict:
    return {"version": REGISTRY_VERSION, "default": None, "profiles": {}}


def load_registry(root: str = ROOT) -> dict:
    """Read profiles.json. Returns empty registry if file missing or corrupt."""
    path = _registry_path(root)
    if not os.path.isfile(path):
        return _empty_registry()
    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _empty_registry()
        data.setdefault("version", REGISTRY_VERSION)
        data.setdefault("default", None)
        data.setdefault("profiles", {})
        return data
    except (json.JSONDecodeError, OSError):
        return _empty_registry()


def _empty_profile(name: str) -> dict:
    """Default profile spec for new profile_create."""
    return {
        "name": name,
        "description": "",
        "caps": ["vision"],
        "viewport": {"width": 1280, "height": 800},
        "locale": "en-US",
        "timezone": "Asia/Jakarta",
        "fingerprint": {"hideWebDriver": True, "stealth": True},
        "network": {},
        "tags": [],
    }


def save_registry(data: dict, root: str = ROOT) -> None:
    """Atomic write of registry. Caller should hold registry_lock."""
    _atomic_write_json(_registry_path(root), data)


# ---------- profile CRUD ----------

def list_profiles(root: str = ROOT) -> dict:
    """Return {default: str|None, profiles: [{name, caps, viewport, ...}]}."""
    reg = load_registry(root)
    out = []
    for name, entry in reg.get("profiles", {}).items():
        if not isinstance(entry, dict) or "path" not in entry:
            continue  # malformed entry, skip
        profile_path = os.path.join(root, entry["path"])
        spec = _read_profile_file(profile_path)
        if not spec:
            continue
        out.append({
            "name": name,
            "caps": spec.get("caps", []),
            "tags": spec.get("tags", []),
            "description": spec.get("description", ""),
            "viewport": spec.get("viewport", {}),
            "locale": spec.get("locale", "en-US"),
            "timezone": spec.get("timezone", "UTC"),
            "userAgent": spec.get("userAgent"),
            "proxy": spec.get("proxy"),
            "path": profile_path,
            "config_path": os.path.join(root, "configs", f"{name}.json"),
            "data_dir": os.path.join(root, "profiles", name),
        })
    default = reg.get("default")
    return {"default": default, "profiles": out}


def get_profile(name: str, root: str = ROOT) -> Optional[Profile]:
    reg = load_registry(root)
    entry = reg.get("profiles", {}).get(name)
    if not entry or not isinstance(entry, dict) or "path" not in entry:
        return None
    spec_path = os.path.join(root, entry["path"])
    spec = _read_profile_file(spec_path)
    if not spec:
        return None
    return profile_from_dict(spec)


def update_profile(name: str, updates: dict, root: str = ROOT) -> Profile:
    """Update an existing profile's spec fields. Kills live subprocesses
    (since user-data-dir / config unchanged but mode-related config may differ).

    Returns the new Profile.
    """
    with registry_lock(root):
        reg = load_registry(root)
        entry = reg.get("profiles", {}).get(name)
        if not entry or not isinstance(entry, dict) or "path" not in entry:
            raise ValueError(f"profile not found: {name!r}")
        spec_path = os.path.join(root, entry["path"])
        spec = _read_profile_file(spec_path)
        if not spec:
            raise ValueError(f"profile spec missing: {spec_path}")
        # Merge updates (caller is responsible for valid fields)
        for k, v in updates.items():
            if k in ("name",):
                raise ValueError("cannot change profile name via update")
            spec[k] = v
        # Re-validate
        errs = validate_profile_spec(spec)
        if errs:
            raise ValueError("invalid update: " + "; ".join(errs))
        profile = profile_from_dict(spec)
        # Rewrite spec
        _atomic_write_json(spec_path, profile.to_dict())
        # Rewrite default-mode patchright config (per-spawn variants will be
        # regenerated when opened with a different mode)
        default_mode = profile_schema_module.default_mode()
        _atomic_write_json(profile.config_path(root), to_patchright_config(profile, mode=default_mode))
    return profile


def create_profile(spec: dict, root: str = ROOT) -> Profile:
    """Create profile: validate, write spec + patchright config, register."""
    errs = validate_profile_spec(spec)
    if errs:
        raise ValueError("invalid profile spec: " + "; ".join(errs))
    name = spec["name"]
    with registry_lock(root):
        reg = load_registry(root)
        if name in reg["profiles"]:
            raise ValueError(f"profile {name!r} already exists")
        # Build Profile from spec (no mode — mode is per-spawn)
        profile = profile_from_dict(spec)
        # Make dirs
        os.makedirs(profile.data_dir(root), exist_ok=True)
        os.makedirs(os.path.dirname(profile.config_path(root)), exist_ok=True)
        dl = profile.downloads_dir(root)
        os.makedirs(dl, exist_ok=True)
        # Write profile spec
        profile_json_path = os.path.join(root, "profiles", f"{name}.json")
        _atomic_write_json(profile_json_path, profile.to_dict())
        # Write patchright config (default mode = auto-detect; per-spawn override)
        default_mode = profile_schema_module.default_mode()
        cfg = to_patchright_config(profile, mode=default_mode)
        _atomic_write_json(profile.config_path(root), cfg)
        # Register
        reg["profiles"][name] = {"path": os.path.relpath(profile_json_path, root)}
        if reg.get("default") is None:
            reg["default"] = name
        save_registry(reg, root)
    return profile


def delete_profile(name: str, root: str = ROOT) -> None:
    """Remove profile: kill subprocess (caller must do that), wipe dirs, unregister."""
    with registry_lock(root):
        reg = load_registry(root)
        if name not in reg["profiles"]:
            raise ValueError(f"profile not found: {name!r}")
        entry = reg["profiles"].pop(name)
        # Switch default if this was it
        if reg.get("default") == name:
            reg["default"] = next(iter(reg["profiles"]), None)
        save_registry(reg, root)
    # Wipe outside lock (slow filesystem op)
    import shutil
    for relpath in ("profiles/" + name, "configs/" + name + ".json",
                    os.path.dirname(entry["path"]) + "/" + name if False else entry["path"]):
        # entry["path"] is the profile JSON
        full = os.path.join(root, entry["path"])
        if os.path.isfile(full):
            os.unlink(full)
        data_dir = os.path.join(root, "profiles", name)
        if os.path.isdir(data_dir):
            shutil.rmtree(data_dir, ignore_errors=True)
        cfg_path = os.path.join(root, "configs", f"{name}.json")
        if os.path.isfile(cfg_path):
            os.unlink(cfg_path)


def set_default(name: str, root: str = ROOT) -> None:
    with registry_lock(root):
        reg = load_registry(root)
        if name not in reg["profiles"]:
            raise ValueError(f"profile not found: {name!r}")
        reg["default"] = name
        save_registry(reg, root)


def rename_profile(old: str, new: str, root: str = ROOT) -> None:
    """Rename profile: move data dir, rewrite spec/config, update registry."""
    from profile_schema import SLUG_RE
    if not SLUG_RE.match(new):
        raise ValueError(f"invalid name {new!r}")
    with registry_lock(root):
        reg = load_registry(root)
        if old not in reg["profiles"]:
            raise ValueError(f"profile not found: {old!r}")
        if new in reg["profiles"]:
            raise ValueError(f"profile {new!r} already exists")
        old_entry = reg["profiles"].pop(old)
        old_spec = _read_profile_file(os.path.join(root, old_entry["path"]))
        old_spec["name"] = new
        # Rewrite spec with new name
        new_spec_path = os.path.join(root, "profiles", f"{new}.json")
        _atomic_write_json(new_spec_path, old_spec)
        # Move data dir
        old_data = os.path.join(root, "profiles", old)
        new_data = os.path.join(root, "profiles", new)
        if os.path.isdir(old_data):
            os.rename(old_data, new_data)
        # Rewrite patchright config (mode default; per-spawn override)
        profile = profile_from_dict(old_spec)
        default_mode = profile_schema_module.default_mode()
        _atomic_write_json(profile.config_path(root), to_patchright_config(profile, mode=default_mode))
        # Remove old files
        old_spec_path = os.path.join(root, old_entry["path"])
        if os.path.isfile(old_spec_path):
            os.unlink(old_spec_path)
        old_cfg = os.path.join(root, "configs", f"{old}.json")
        if os.path.isfile(old_cfg):
            os.unlink(old_cfg)
        # Update registry
        reg["profiles"][new] = {"path": os.path.relpath(new_spec_path, root)}
        if reg.get("default") == old:
            reg["default"] = new
        save_registry(reg, root)


def _read_profile_file(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    with open(path) as f:
        return json.load(f)


# ---------- migrations from old registry format ----------

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print(json.dumps(list_profiles(), indent=2, default=str))
    else:
        print("usage: registry.py list")
        print("usage: registry.py list")
