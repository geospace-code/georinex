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


def test_batch_convert_obs():
    pytest.importorskip('netCDF4')
    pat = '*o'

    flist = R.glob(pat)  # all OBS 2 files

    with tempfile.TemporaryDirectory() as outdir:
        gr.batch_convert(R, pat, outdir)

        for fn in flist:
            outfn = Path(outdir) / (fn.name + '.nc')
            assert outfn.is_file(), f'{outfn}'
            assert outfn.stat().st_size > 30000, f'{outfn}'

            truth = gr.load(fn)
            obs = gr.load(outfn)

            assert obs.equals(truth), f'{outfn}  {fn}'


def test_batch_convert_nav():
    pytest.importorskip('netCDF4')
    pat = '*n'

    flist = R.glob(pat)  # all OBS 2 files

    with tempfile.TemporaryDirectory() as outdir:
        gr.batch_convert(R, pat, outdir)

        for fn in flist:
            outfn = Path(outdir) / (fn.name + '.nc')
            assert outfn.is_file(), f'{outfn}'
            assert outfn.stat().st_size > 15000, f'{outfn}'

            truth = gr.load(fn)
            nav = gr.load(outfn)

            assert nav.equals(truth), f'{outfn}  {fn}'


def test_batch_convert_bad():
    pat = '*o'

    with pytest.raises(TypeError):
        with tempfile.TemporaryDirectory() as baddir:
            gr.batch_convert(baddir, pat)

    with pytest.raises(FileNotFoundError):
        with tempfile.TemporaryDirectory() as outdir:
            gr.batch_convert(outdir, pat, outdir)


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
    pytest.main(['-x', __file__])
