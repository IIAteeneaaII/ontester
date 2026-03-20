import json
from pathlib import Path
from typing import Optional

STATE_FILE = Path("C:/ONT/update_state.json")


def _read_state() -> dict:
    if not STATE_FILE.exists():
        return {}

    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(data: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def set_pending_update_target_version(version: str, installer_name: str | None = None) -> None:
    state = _read_state()
    state["pending_target_version"] = version
    if installer_name:
        state["pending_installer_name"] = installer_name
    _write_state(state)


def get_pending_update_target_version() -> Optional[str]:
    state = _read_state()
    return state.get("pending_target_version")


def clear_pending_update_target_version() -> None:
    state = _read_state()
    state.pop("pending_target_version", None)
    state.pop("pending_installer_name", None)
    _write_state(state)


def set_last_reported_installed_version(version: str) -> None:
    state = _read_state()
    state["last_reported_installed_version"] = version
    _write_state(state)


def get_last_reported_installed_version() -> Optional[str]:
    state = _read_state()
    return state.get("last_reported_installed_version")