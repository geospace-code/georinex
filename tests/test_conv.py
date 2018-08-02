#!/usr/bin/env python
"""
Self-test file, registration case
for OBS RINEX reader
"""
import tempfile
import pytest
import xarray
from pathlib import Path
import georinex as gr
#
R = Path(__file__).parent


def test_netcdf_read():
    pytest.importorskip('netCDF4')

    obs, nav = gr.readrinex(R/'r2all.nc')
    assert isinstance(obs, xarray.Dataset)


def test_netcdf_write():
    """
    NetCDF4 is fuzzy about filenames, it doesn't like arbitrary tempfile.NamedTemporaryFile names
    """
    pytest.importorskip('netCDF4')

    with tempfile.TemporaryDirectory() as D:
        fn = Path(D)/'rw.nc'
        obs, nav = gr.readrinex(R/'demo.10o', outfn=fn)

        wobs, wnav = gr.readrinex(fn)

        # MUST be under context manager for lazy loading
        assert obs.equals(wobs)


def test_obsdata():
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r2all.nc', group='OBS', autoclose=True)

    obs, nav = gr.readrinex(R/'demo.10o')
    assert obs.equals(truth)


def test_navdata():
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r2all.nc', group='NAV', autoclose=True)
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
    pytest.main(['-x', __file__])
