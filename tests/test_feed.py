"""Tests for feed.build_output_args (dumphfdl --output argv builder)."""

from __future__ import annotations

from pathlib import Path

from hfdl_recorder.core.feed import build_output_args


def test_local_json_default():
    args = build_output_args(
        {"local_json": True},
        spool_dir=Path("/var/lib/hfdl-recorder"),
        radiod_id="rx888",
        band_name="HFDL13",
    )
    assert args == [
        "--output",
        "decoded:json:file:path=/var/lib/hfdl-recorder/rx888/HFDL13.json",
    ]


def test_local_json_off():
    args = build_output_args(
        {"local_json": False},
        spool_dir=Path("/var/lib/hfdl-recorder"),
        radiod_id="rx888",
        band_name="HFDL13",
    )
    assert args == []


def test_airframes_appended():
    args = build_output_args(
        {"local_json": True, "airframes_io": True},
        spool_dir=Path("/var/lib/hfdl-recorder"),
        radiod_id="rx888",
        band_name="HFDL13",
    )
    # Order: local first, airframes second.
    assert args[:2] == [
        "--output",
        "decoded:json:file:path=/var/lib/hfdl-recorder/rx888/HFDL13.json",
    ]
    assert args[2:] == [
        "--output",
        "decoded:json:tcp:address=feed.airframes.io,port=5556",
    ]


def test_extra_tcp_sink():
    args = build_output_args(
        {
            "local_json": False,
            "extra": [
                {"proto": "tcp", "host": "agg.example", "port": 5556},
            ],
        },
        spool_dir=Path("/var/lib/hfdl-recorder"),
        radiod_id="rx888",
        band_name="HFDL13",
    )
    assert args == [
        "--output",
        "decoded:json:tcp:address=agg.example,port=5556",
    ]


def test_extra_skipped_when_incomplete():
    args = build_output_args(
        {
            "local_json": False,
            "extra": [
                {"proto": "tcp", "host": "", "port": 5556},      # missing host
                {"proto": "tcp", "host": "agg", "port": None},   # missing port
                {"proto": "weird", "host": "agg", "port": 1},    # unsupported
            ],
        },
        spool_dir=Path("/var/lib/hfdl-recorder"),
        radiod_id="rx888",
        band_name="HFDL13",
    )
    assert args == []
