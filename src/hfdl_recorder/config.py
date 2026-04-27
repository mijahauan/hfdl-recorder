"""TOML config loader and defaults for hfdl-recorder."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

from hfdl_recorder.bands import HFDL_BANDS, HfdlBand


DEFAULT_CONFIG_PATH = Path("/etc/hfdl-recorder/hfdl-recorder-config.toml")

DEFAULTS: dict[str, Any] = {
    "paths": {
        "dumphfdl":  "/opt/hfdl-recorder/bin/dumphfdl",
        "spool_dir": "/var/lib/hfdl-recorder",
        "log_dir":   "/var/log/hfdl-recorder",
        "systable":  "/var/lib/hfdl-recorder/systable.conf",
    },
    "sinks": {
        "local_json":   True,
        "airframes_io": False,
    },
}

# Encoding integer matches ka9q-python's Encoding enum (s16be = 2). The
# radiod HFDL fragment ships every band as s16be, so we hard-code it here.
DEFAULT_PRESET = "iq"
DEFAULT_ENCODING = "s16be"


def load_config(path: Path | None = None) -> dict:
    """Load and merge config with defaults."""
    config_path = path or Path(
        os.environ.get("HFDL_RECORDER_CONFIG", str(DEFAULT_CONFIG_PATH))
    )
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    raw.setdefault("paths", {})
    for key, val in DEFAULTS["paths"].items():
        raw["paths"].setdefault(key, val)

    raw.setdefault("sinks", {})
    for key, val in DEFAULTS["sinks"].items():
        raw["sinks"].setdefault(key, val)

    return raw


def resolve_radiod_block(config: dict, radiod_id: str | None) -> dict:
    """Find the [[radiod]] block matching radiod_id.

    If radiod_id is None, the config must contain exactly one [[radiod]].
    """
    radiod_blocks = config.get("radiod", [])
    if isinstance(radiod_blocks, dict):
        radiod_blocks = [radiod_blocks]

    if not radiod_blocks:
        raise ValueError("Config contains no [[radiod]] blocks")

    if radiod_id is None:
        if len(radiod_blocks) != 1:
            raise ValueError(
                f"--radiod-id required: config has {len(radiod_blocks)} "
                f"[[radiod]] blocks"
            )
        return radiod_blocks[0]

    for block in radiod_blocks:
        if block.get("id") == radiod_id:
            return block

    available = [b.get("id", "<unnamed>") for b in radiod_blocks]
    raise ValueError(
        f"No [[radiod]] block with id={radiod_id!r}. "
        f"Available: {', '.join(available)}"
    )


def get_enabled_band_names(radiod_block: dict) -> list[str]:
    """Return the list of band names enabled for this radiod, in config order."""
    bands_block = radiod_block.get("bands", {})
    return list(bands_block.get("enabled", []))


def get_enabled_bands(radiod_block: dict) -> list[HfdlBand]:
    """Resolve enabled band names against the static HFDL_BANDS table.

    Unknown names raise ValueError so misconfigurations fail loud rather
    than silently dropping a band the operator thought was enabled.
    """
    resolved: list[HfdlBand] = []
    for name in get_enabled_band_names(radiod_block):
        band = HFDL_BANDS.get(name)
        if band is None:
            raise ValueError(
                f"Unknown HFDL band {name!r}. "
                f"Valid: {', '.join(sorted(HFDL_BANDS))}"
            )
        resolved.append(band)
    return resolved


def resolve_radiod_status(radiod_block: dict) -> str:
    """Resolve the radiod mDNS hostname.

    Precedence:
      1. RADIOD_<ID>_STATUS from environment (sigmond-supplied)
      2. radiod_status field in the [[radiod]] block (standalone fallback)
    """
    radiod_id = radiod_block.get("id", "")
    env_key = f"RADIOD_{radiod_id.upper().replace('-', '_')}_STATUS"
    from_env = os.environ.get(env_key)
    if from_env:
        return from_env

    status = radiod_block.get("radiod_status")
    if not status:
        raise ValueError(
            f"[[radiod]] id={radiod_id!r} has no radiod_status and "
            f"{env_key} is not set in the environment"
        )
    return status
