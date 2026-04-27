"""Static HFDL band table.

Per-band entries combine:
  - Band center frequency in Hz (matches radiod fragment ``freq``)
  - IQ sample rate in Hz (matches radiod fragment ``samprate``)
  - List of in-band channel frequencies (kHz, float) passed as positional
    args to ``dumphfdl`` to select which sub-channels to demodulate.

Sources of truth:
  - Sample rates and centers: radiod fragment
    ``ka9q-radio/config/fragments/hfdl.conf`` (also vendored by wsprdaemon
    at ``radiod@rx888-wsprdaemon.conf.d/51-hfdl.conf``).
  - Channel frequency lists: ``ka9q-radio/aux/start-hfdl.sh``.

Band names match the radiod section names (``[HFDL21]``, ``[HFDL13]``, …),
so an operator can grep for the same identifier in both configs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HfdlBand:
    name: str
    center_hz: int
    samprate_hz: int
    channels_khz: tuple[float, ...]


HFDL_BANDS: dict[str, HfdlBand] = {
    "HFDL2":  HfdlBand("HFDL2",   2_980_000,  80_000,
                       (2941, 2944, 2992, 2998, 3007, 3016)),
    "HFDL3":  HfdlBand("HFDL3",   3_477_000,  50_000,
                       (3455, 3497)),
    "HFDL4":  HfdlBand("HFDL4",   4_672_000,  40_000,
                       (4654, 4660, 4681, 4687)),
    "HFDL5":  HfdlBand("HFDL5",   5_587_000, 277_200,
                       (5451, 5502, 5508, 5514, 5529, 5538, 5544, 5547,
                        5583, 5589, 5622, 5652, 5655, 5720)),
    "HFDL6":  HfdlBand("HFDL6",   6_622_000, 192_000,
                       (6529, 6532, 6535, 6559, 6565, 6589, 6596, 6619,
                        6628, 6646, 6652, 6661, 6712)),
    "HFDL8":  HfdlBand("HFDL8",   8_902_500, 160_000,
                       (8825, 8834, 8843, 8885, 8886, 8894, 8912, 8921,
                        8927, 8936, 8939, 8942, 8948, 8957, 8977)),
    "HFDL10": HfdlBand("HFDL10", 10_061_500,  80_000,
                       (10027, 10030, 10060, 10063, 10066, 10075, 10081,
                        10084, 10087, 10093)),
    "HFDL11": HfdlBand("HFDL11", 11_287_000, 220_000,
                       (11184, 11306, 11312, 11318, 11321, 11327, 11348,
                        11354, 11384, 11387)),
    "HFDL13": HfdlBand("HFDL13", 13_310_000, 100_000,
                       (13264, 13270, 13276, 13303, 13312, 13315, 13321,
                        13324, 13342, 13351, 13354)),
    "HFDL15": HfdlBand("HFDL15", 15_025_000,  12_000,
                       (15025,)),
    "HFDL17": HfdlBand("HFDL17", 17_944_000, 100_000,
                       (17901, 17912, 17916, 17919, 17922, 17928, 17934,
                        17958, 17967, 17985)),
    "HFDL21": HfdlBand("HFDL21", 21_964_000,  80_000,
                       (21928, 21931, 21934, 21937, 21949, 21955, 21982,
                        21990, 21997)),
}


# Curated default for the config template: bands with consistently high
# global traffic across day/night propagation. Skips HFDL15 (squitter-only,
# narrow-IQ) and the lowest-yield bands.
DEFAULT_ENABLED_BANDS: tuple[str, ...] = (
    "HFDL21", "HFDL13", "HFDL11", "HFDL10",
    "HFDL8",  "HFDL6",  "HFDL5",
)
