#!/usr/bin/env python
"""
Self-test file, registration case
for OBS RINEX reader
"""
import pytest
import xarray
from pytest import approx
from pathlib import Path
import georinex as gr
import os
#
R = Path(__file__).parent / 'data'


@pytest.mark.xfail(os.name == 'nt', reason='Windows PermissionError for missing files')
def test_bad_files(tmp_path):
    emptyfn = tmp_path/'nonexistingfilename'
    emptyfn.touch()
    emptyfnrinex = tmp_path/'nonexistingfilename.18o'
    emptyfnrinex.touch()
    emptyfnNC = tmp_path/'nonexistingfilename.nc'
    emptyfnNC.touch()

    nonexist = tmp_path/'nonexist'  # don't touch

    with pytest.raises(ValueError):
        gr.load(emptyfn)

    with pytest.raises(ValueError):
        gr.load(emptyfnrinex)

    with pytest.raises(FileNotFoundError):
        gr.load(nonexist)

    with pytest.raises(ValueError):
        gr.load(emptyfnNC)


def test_netcdf_read():
    pytest.importorskip('netCDF4')

    dat = gr.load(R/'r2all.nc')

    assert isinstance(dat, dict), f'{type(dat)}'
    assert isinstance(dat['obs'], xarray.Dataset)


def test_netcdf_write(tmp_path):
    """
    NetCDF4 wants suffix .nc -- arbitrary tempfile.NamedTemporaryFile names do NOT work!
    """
    pytest.importorskip('netCDF4')

    outdir = tmp_path
    fn = outdir / 'rw.nc'
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


@pytest.mark.parametrize('dtype', ['OBS', 'NAV'])
def test_nc_load(dtype):
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r2all.nc', group=dtype)

    obs = gr.load(R/f'demo.10{dtype[0].lower()}')
    assert obs.equals(truth)


if __name__ == '__main__':
    pytest.main(['-xrsv', __file__])
