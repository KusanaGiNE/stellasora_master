"""Configuration loader for automation modules."""
from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
DEFAULT_CONFIG: Dict[str, Any] = {
    "adb_path": "",
    "default_instance": 1,
    "adb_port": 16384,
}

_CONFIG_CACHE: Dict[str, Any] | None = None
_CONFIG_LOCK = Lock()


def _load_config() -> Dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                config.update(data)
        except json.JSONDecodeError as exc:
            raise ValueError(f"配置文件格式错误: {CONFIG_PATH}\n{exc}") from exc
    return config


def get_config() -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = _load_config()
    return dict(_CONFIG_CACHE)


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = (CONFIG_PATH.parent / path).resolve()
    return path


def get_adb_path(raise_on_missing: bool = True) -> Path | None:
    config = get_config()
    raw = config.get("adb_path")
    if not raw:
        if raise_on_missing:
            raise FileNotFoundError("ADB 路径未配置，请在设置页面填写 adb_path")
        return None

    path = resolve_path(raw)
    if not path:
        if raise_on_missing:
            raise FileNotFoundError("无法解析 ADB 路径，请在设置页面重新填写")
        return None

    if not path.exists():
        if raise_on_missing:
            raise FileNotFoundError(f"未找到 ADB 工具，请检查设置中的路径: {path}")
        return path

    return path


def get_default_instance() -> int:
    config = get_config()
    try:
        value = int(config.get("default_instance", 1))
    except (TypeError, ValueError):
        value = 1
    return value

def get_adb_port() -> int:
    config = get_config()
    try:
        value = int(config.get("adb_port", 16384))
    except (TypeError, ValueError):
        value = 16384
    return value


def update_config(values: Dict[str, Any]) -> Dict[str, Any]:
    allowed_keys = set(DEFAULT_CONFIG.keys())
    filtered = {k: v for k, v in values.items() if k in allowed_keys}

    with _CONFIG_LOCK:
        current = _load_config()
        current.update(filtered)
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w", encoding="utf-8") as fh:
            json.dump(current, fh, ensure_ascii=False, indent=2)

        global _CONFIG_CACHE
        _CONFIG_CACHE = dict(current)

    return dict(current)


def reload_config() -> Dict[str, Any]:
    global _CONFIG_CACHE
    with _CONFIG_LOCK:
        _CONFIG_CACHE = _load_config()
        return dict(_CONFIG_CACHE)
