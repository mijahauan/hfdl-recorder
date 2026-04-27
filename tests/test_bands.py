"""Static-table integrity checks for HFDL_BANDS."""

from __future__ import annotations

import pytest

from hfdl_recorder.bands import DEFAULT_ENABLED_BANDS, HFDL_BANDS


def test_band_count():
    # 12 HFDL bands per the radiod fragment 51-hfdl.conf.
    assert len(HFDL_BANDS) == 12


def test_band_names_match_keys():
    for name, band in HFDL_BANDS.items():
        assert band.name == name


def test_band_centers_unique():
    centers = [b.center_hz for b in HFDL_BANDS.values()]
    assert len(set(centers)) == len(centers)


def test_default_enabled_bands_valid():
    for name in DEFAULT_ENABLED_BANDS:
        assert name in HFDL_BANDS, f"{name} is not in HFDL_BANDS"


@pytest.mark.parametrize("name", list(HFDL_BANDS))
def test_band_has_channels(name):
    band = HFDL_BANDS[name]
    assert len(band.channels_khz) >= 1
    # Every channel kHz should fall inside the IQ bandwidth around the
    # band center (samprate/2 on each side, in kHz).
    half_bw_khz = band.samprate_hz / 2 / 1000
    center_khz = band.center_hz / 1000
    for ch in band.channels_khz:
        assert abs(ch - center_khz) <= half_bw_khz, (
            f"{name}: channel {ch} kHz outside ±{half_bw_khz} kHz of "
            f"center {center_khz} kHz"
        )
