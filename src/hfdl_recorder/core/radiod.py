"""Thin wrapper around ka9q-python ``RadiodControl.ensure_channel`` for HFDL.

Per CLIENT-CONTRACT.md §7, clients never pass ``destination=`` — radiod
+ ka9q-python deterministically derive the multicast group. We read the
resolved address back from ``ChannelInfo`` for inventory purposes.

The radiod HFDL fragment ships every band as ``mode=iq`` ``encoding=s16be``
with band-specific ``samprate``. We hard-code those here so the band
table in :mod:`hfdl_recorder.bands` stays purely descriptive.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from hfdl_recorder.bands import HfdlBand

logger = logging.getLogger(__name__)


HFDL_PRESET = "iq"
# ka9q.Encoding.S16BE = 2 (matches the per-band ``encoding = s16be`` in
# the radiod HFDL fragment).
HFDL_ENCODING = 2


@dataclass(frozen=True)
class ResolvedChannel:
    band: HfdlBand
    multicast_address: str
    port: int


def ensure_band_channel(control, band: HfdlBand) -> ResolvedChannel:
    """Provision (or look up) a radiod channel for one HFDL band.

    ``control`` is a ka9q.RadiodControl instance. We pass through to
    ``ensure_channel`` and surface the resolved multicast destination
    so callers can subscribe via MultiStream.
    """
    info = control.ensure_channel(
        frequency_hz=float(band.center_hz),
        preset=HFDL_PRESET,
        sample_rate=band.samprate_hz,
        encoding=HFDL_ENCODING,
    )
    logger.info(
        "Provisioned %s: %d Hz @ %d S/s -> %s:%d",
        band.name, band.center_hz, band.samprate_hz,
        info.multicast_address, info.port,
    )
    return ResolvedChannel(
        band=band,
        multicast_address=info.multicast_address,
        port=info.port,
    )
