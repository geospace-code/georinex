#!/usr/bin/env python
"""
Self-test file, registration case
for OBS RINEX reader
"""
import pytest
import xarray
from pathlib import Path
import georinex as gr

R = Path(__file__).parent


def test_obsdata():
    truth = xarray.open_dataset(R/'test2all.nc', group='OBS')

    obs, nav = gr.readrinex(R/'demo.10o')
    assert obs.equals(truth)


def test_navdata():
    truth = xarray.open_dataset(R/'test2all.nc', group='NAV')
    obs, nav = gr.readrinex(R/'demo.10n')

    assert nav.equals(truth)


def test_obsheader():
    # %% rinex 2
    hdr = gr.rinexheader(R/'demo.10o')
    assert isinstance(hdr, dict)
    assert len(hdr['position']) == 3
    # %% rinex 3
    hdr = gr.rinexheader(R/'demo3.10o')
    assert isinstance(hdr, dict)
    assert len(hdr['position']) == 3


def test_navheader():
    # %% rinex 2
    hdr = gr.rinexheader(R/'demo.10n')
    assert isinstance(hdr, dict)
    assert int(hdr['version']) == 2
    # %% rinex 3
    hdr = gr.rinexheader(R/'demo3.10n')
    assert isinstance(hdr, dict)
    assert int(hdr['version']) == 3


if __name__ == '__main__':
    pytest.main()
