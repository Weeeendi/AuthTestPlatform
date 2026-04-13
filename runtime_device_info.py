# coding:utf-8
"""In-memory runtime device info.

This replaces the old paramConfig.json file.

Requirements:
- Do not persist as default fill data
- Always empty on each app start/login session
- Cleared on logout

The Setting page writes into this module; the Auth/Test page reads from it.
"""

from __future__ import annotations

from threading import RLock
from typing import Any, Dict


_LOCK = RLock()
_DEFAULT: Dict[str, Any] = {
    'manual_host': False,
    'host': '',
    'port': '',
    'query_pid': '',
    'hardware_version': '',
    'burning_pid': False,
    'burning_host': False,
}
_DEVICE_INFO: Dict[str, Any] = dict(_DEFAULT)


def get_default_device_info() -> Dict[str, Any]:
    return dict(_DEFAULT)


def clear_device_info() -> None:
    global _DEVICE_INFO
    with _LOCK:
        _DEVICE_INFO = dict(_DEFAULT)


def set_device_info(info: Dict[str, Any]) -> None:
    """Replace runtime device info (merged with defaults)."""
    global _DEVICE_INFO
    if not isinstance(info, dict):
        return

    with _LOCK:
        merged = dict(_DEFAULT)
        for key in merged.keys():
            if key in info:
                merged[key] = info.get(key)
        _DEVICE_INFO = merged


def update_device_info(partial: Dict[str, Any]) -> None:
    """Update subset of fields."""
    if not isinstance(partial, dict):
        return

    with _LOCK:
        for key, value in partial.items():
            if key in _DEFAULT:
                _DEVICE_INFO[key] = value


def get_device_info() -> Dict[str, Any]:
    with _LOCK:
        return dict(_DEVICE_INFO)
