"""Tests for contract v0.4 inventory/validate JSON builders."""

from __future__ import annotations

from pathlib import Path

from hfdl_recorder.config import load_config
from hfdl_recorder.contract import (
    CONTRACT_VERSION,
    build_inventory,
    build_validate,
)

FIXTURE = Path(__file__).parent / "fixtures" / "test-config.toml"


def test_contract_version_is_0_4():
    assert CONTRACT_VERSION == "0.4"


def test_inventory_required_top_level_keys():
    cfg = load_config(FIXTURE)
    inv = build_inventory(cfg, FIXTURE)
    for key in (
        "client", "version", "contract_version", "config_path",
        "log_paths", "log_level", "instances", "deps", "issues",
    ):
        assert key in inv, f"missing top-level inventory key: {key}"
    assert inv["client"] == "hfdl-recorder"
    assert inv["contract_version"] == "0.4"


def test_inventory_instance_shape():
    cfg = load_config(FIXTURE)
    inv = build_inventory(cfg, FIXTURE)
    assert len(inv["instances"]) == 1
    inst = inv["instances"][0]
    assert inst["instance"] == "test-rx888"
    assert inst["radiod_id"] == "test-rx888"
    assert inst["modes"] == ["hfdl"]
    assert inst["bands"] == ["HFDL21", "HFDL13", "HFDL5"]
    assert inst["ka9q_channels"] == 3
    # frequencies sorted ascending (band centers).
    assert inst["frequencies_hz"] == sorted(inst["frequencies_hz"])
    assert inst["data_destination"] is None  # contract §7
    assert inst["uses_timing_calibration"] is False


def test_validate_passes_with_fixture():
    cfg = load_config(FIXTURE)
    payload = build_validate(cfg, FIXTURE)
    fails = [i for i in payload["issues"] if i["severity"] == "fail"]
    assert payload["ok"] is True, f"unexpected fails: {fails}"


def test_validate_fails_when_dumphfdl_missing(tmp_path):
    cfg = load_config(FIXTURE)
    cfg["paths"]["dumphfdl"] = str(tmp_path / "not-a-binary")
    payload = build_validate(cfg)
    assert payload["ok"] is False
    fails = [i for i in payload["issues"] if i["severity"] == "fail"]
    assert any("dumphfdl not found" in i["message"] for i in fails)


def test_validate_flags_unknown_band(tmp_path):
    cfg = load_config(FIXTURE)
    cfg["radiod"][0]["bands"]["enabled"] = ["HFDL21", "BOGUS"]
    payload = build_validate(cfg)
    assert payload["ok"] is False
    assert any(
        i["severity"] == "fail" and "BOGUS" in i["message"]
        for i in payload["issues"]
    )


def test_validate_flags_duplicate_band():
    cfg = load_config(FIXTURE)
    cfg["radiod"][0]["bands"]["enabled"] = ["HFDL21", "HFDL21"]
    payload = build_validate(cfg)
    assert payload["ok"] is False
    assert any(
        i["severity"] == "fail" and "twice" in i["message"]
        for i in payload["issues"]
    )


def test_validate_fails_airframes_without_station_id():
    cfg = load_config(FIXTURE)
    cfg["station"]["station_id"] = ""
    cfg["sinks"]["airframes_io"] = True
    payload = build_validate(cfg)
    assert payload["ok"] is False
    assert any(
        i["severity"] == "fail" and "station_id" in i["message"]
        for i in payload["issues"]
    )
