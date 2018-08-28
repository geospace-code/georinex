#!/usr/bin/env python
"""
Self-test file, registration case
for OBS RINEX reader
"""
import tempfile
import pytest
import xarray
from pytest import approx
from pathlib import Path
import georinex as gr
import os
WIN32 = os.name == 'nt'
#
R = Path(__file__).parent


@pytest.mark.xfail(WIN32, reason='Windows PermissionError for missing files')
def test_bad_files():
    with pytest.raises(ValueError):
        with tempfile.NamedTemporaryFile() as f:
            gr.load(f.name)

    with pytest.raises(ValueError):
        with tempfile.NamedTemporaryFile(suffix='.18o') as f:
            fn = f.name
            gr.load(f.name)

    with pytest.raises(FileNotFoundError):
        gr.load(fn)

    with pytest.raises(ValueError):
        with tempfile.NamedTemporaryFile(suffix='.nc') as f:
            gr.load(f.name)


def test_netcdf_read():
    pytest.importorskip('netCDF4')

    dat = gr.load(R/'r2all.nc')

    assert isinstance(dat, dict), f'{type(dat)}'
    assert isinstance(dat['obs'], xarray.Dataset)


def test_netcdf_write():
    """
    NetCDF4 wants suffix .nc -- arbitrary tempfile.NamedTemporaryFile names do NOT work!
    """
    pytest.importorskip('netCDF4')

    with tempfile.TemporaryDirectory() as D:
        fn = Path(D)/'rw.nc'
        obs = gr.load(R/'demo.10o', out=fn)

        wobs = gr.load(fn)

        # MUST be under context manager for lazy loading
        assert obs.equals(wobs)


def test_locs():
    pytest.importorskip('pymap3d')

    pat = ['*o',
           '*O.rnx', '*O.rnx.gz',
           '*O.crx', '*O.crx.gz']

    flist = gr.globber(R, pat)

    locs = gr.getlocations(flist)

    assert locs.loc['demo.10o'].values == approx([41.3887, 2.112, 30])


def test_obsdata():
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r2all.nc', group='OBS', autoclose=True)

    obs = gr.load(R/'demo.10o')
    assert obs.equals(truth)


def test_navdata():
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r2all.nc', group='NAV', autoclose=True)
    nav = gr.load(R/'demo.10n')

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
    pytest.main(['-xrsv', __file__])
