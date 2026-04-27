"""Translate the [sinks] config block into dumphfdl ``--output`` arguments.

dumphfdl's output spec syntax (one ``--output`` arg per sink):

    decoded:json:file:path=<path>
    decoded:json:tcp:address=<host>,port=<port>
    decoded:json:udp:address=<host>,port=<port>
    decoded:text:file:path=<path>

Reference: ``ka9q-radio/aux/start-hfdl.sh`` line 76 and dumphfdl ``--help``.
"""

from __future__ import annotations

from pathlib import Path

AIRFRAMES_HOST = "feed.airframes.io"
AIRFRAMES_PORT = 5556


def build_output_args(
    sinks: dict,
    *,
    spool_dir: Path,
    radiod_id: str,
    band_name: str,
) -> list[str]:
    """Return the list of dumphfdl --output ... arguments for one band.

    Order is stable so the daemon's argv is reproducible across restarts
    (useful for journal grep + golden-string testing).
    """
    args: list[str] = []

    if sinks.get("local_json", True):
        out_path = Path(spool_dir) / radiod_id / f"{band_name}.json"
        args += ["--output", f"decoded:json:file:path={out_path}"]

    if sinks.get("airframes_io", False):
        args += [
            "--output",
            f"decoded:json:tcp:address={AIRFRAMES_HOST},port={AIRFRAMES_PORT}",
        ]

    for extra in sinks.get("extra", []) or []:
        spec = _format_extra(extra)
        if spec:
            args += ["--output", spec]

    return args


def _format_extra(extra: dict) -> str | None:
    """Format one entry of ``sinks.extra`` as a dumphfdl --output spec."""
    proto = (extra.get("proto") or "").lower().strip()
    fmt = (extra.get("format") or "json").lower().strip()
    if proto == "tcp" or proto == "udp":
        host = extra.get("host", "").strip()
        port = extra.get("port")
        if not host or port is None:
            return None
        return f"decoded:{fmt}:{proto}:address={host},port={int(port)}"
    if proto == "file":
        path = extra.get("path", "").strip()
        if not path:
            return None
        return f"decoded:{fmt}:file:path={path}"
    return None
