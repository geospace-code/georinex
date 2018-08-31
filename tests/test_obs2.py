#!/usr/bin/env python
import pytest
import xarray
import tempfile
from pytest import approx
from pathlib import Path
import georinex as gr
import numpy as np
from datetime import datetime
#
R = Path(__file__).parent


def test_blank():
    fn = R/'blank.10o'
    obs = gr.load(fn)
    assert obs is None

    with tempfile.TemporaryDirectory() as outdir:
        outdir = Path(outdir)
        gr.load(fn, outdir)
        assert not (outdir / (fn.name + '.nc')).is_file()

    times = gr.gettime(fn)
    assert times is None


def test_minimal():
    fn = R/'minimal.10o'
    obs = gr.load(fn)
    assert isinstance(obs, xarray.Dataset), f'{type(obs)} should be xarray.Dataset'

    with tempfile.TemporaryDirectory() as outdir:
        outdir = Path(outdir)
        gr.load(fn, outdir)

        outfn = (outdir / (fn.name + '.nc'))
        assert outfn.is_file()
        assert obs.equals(gr.load(outfn)), f'{outfn}  {fn}'

    times = gr.gettime(fn)
    assert np.isnan(times.interval)

    assert obs.fast_processing


def test_fast_slow():
    fn = R/'minimal.10o'
    fobs = gr.load(fn, fast=True)
    sobs = gr.load(fn, fast=False)

    assert fobs.equals(sobs)

    assert fobs.fast_processing
    assert not sobs.fast_processing


def test_meas_continuation():
    """
    tests OBS2 files with more than 10 types of observations
    """
    fn = R/'ab430140.18o.zip'
    obs = gr.load(fn, verbose=True)

    assert len(obs.data_vars) == 20
    for v in ['L1', 'L2', 'C1', 'P2', 'P1', 'S1', 'S2', 'C2', 'L5', 'C5', 'S5',
              'L6', 'C6', 'S6', 'L7', 'C7', 'S7', 'L8', 'C8', 'S8']:
        assert v in obs

    times = obs.time.values.astype('datetime64[us]').astype(datetime)
    assert times.size == 9

    assert obs.fast_processing


def test_meas_one():
    """
    test specifying specific measurements (usually only a few of the thirty or so are needed)
    """
    fn = R/'demo.10o'
    obs = gr.load(fn)
    for v in ['L1', 'L2', 'P1', 'P2', 'C1', 'S1', 'S2']:
        assert v in obs
    assert len(obs.data_vars) == 7

    sv = obs.sv.values
    assert len(sv) == 14
    for s in ['G13', 'R19', 'G32', 'G07', 'R23', 'G31', 'G20', 'R11',
              'G12', 'G26', 'G09', 'G21', 'G15', 'S24']:
        assert s in sv

    assert obs['C1'].sel(sv='G07').values == approx([22227666.76, 25342359.37])
# %% one measurement
    obs = gr.load(fn, meas='C1')
    assert 'L1' not in obs

    C1 = obs['C1']
    assert C1.shape == (2, 14)  # two times, 14 SVs overall for all systems in this file
    assert C1.sel(sv='G07').values == approx([22227666.76, 25342359.37])

    assert obs.fast_processing


def test_meas_two():
    fn = R/'demo.10o'

    C1 = gr.load(fn, meas='C1')['C1']
# %% two NON-SEQUENTIAL measurements
    obs = gr.load(fn, meas=['L1', 'S1'])
    assert 'L2' not in obs

    L1 = obs['L1']
    assert L1.shape == (2, 14)
    assert L1.sel(sv='G07').values == approx([118767195.32608, 133174968.81808])

    S1 = obs['S1']
    assert S1.shape == (2, 14)

    assert (S1.sel(sv='R23') == approx([39., 79.])).all()

    assert not C1.equals(L1)

    assert obs.fast_processing


def test_meas_miss():
    fn = R/'demo.10o'
# %% measurement not in some systems
    obs = gr.load(fn, meas=['S2'])
    assert 'L2' not in obs

    S2 = obs['S2']
    assert S2.shape == (2, 10)  # all NaN SVs are dropped
    assert (S2.sel(sv='G13') == approx([40., 80.])).all()

    with pytest.raises(KeyError):
        S2.sel(sv='R23')

    assert obs.fast_processing
# %% measurement not in any system
    obs = gr.load(fn, meas='nonsense')
    assert obs is None
# %% wildcard
    obs = gr.load(fn, meas='P')
    assert 'L1' not in obs
    assert 'P1' in obs and 'P2' in obs
    assert len(obs.data_vars) == 2

    assert obs.fast_processing


def test_mangled():
    fn = R/'14601736.18o'

    obs = gr.load(fn)

    times = obs.time.values.astype('datetime64[us]').astype(datetime)

    assert (times == (datetime(2018, 6, 22, 6, 17, 30), datetime(2018, 6, 22, 6, 17, 45), datetime(2018, 6, 22, 6, 18))).all()

    assert not obs.fast_processing


def test_Z_lzw():
    pytest.importorskip('unlzw')

    fn = R/'ac660270.18o.Z'

    obs = gr.load(fn)

    hdr = gr.rinexheader(fn)

    assert hdr['t0'] <= obs.time[0].values.astype('datetime64[us]').astype(datetime)

    assert not obs.fast_processing


def test_tlim():
    pytest.importorskip('unlzw')

    obs = gr.load(R/'ac660270.18o.Z', tlim=('2018-01-27T00:19', '2018-01-27T00:19:45'))

    times = obs.time.values.astype('datetime64[us]').astype(datetime).tolist()

    assert times == [datetime(2018, 1, 27, 0, 19),
                     datetime(2018, 1, 27, 0, 19, 15),
                     datetime(2018, 1, 27, 0, 19, 30),
                     datetime(2018, 1, 27, 0, 19, 45)]

    assert not obs.fast_processing


def test_one_sv():
    obs = gr.load(R / 'rinex2onesat.10o')

    assert len(obs.sv) == 1
    assert obs.sv.item() == 'G13'

    times = gr.gettime(R/'rinex2onesat.10o').values.astype('datetime64[us]').astype(datetime)

    assert (times == [datetime(2010, 3, 5, 0, 0), datetime(2010, 3, 5, 0, 0, 30)]).all()

    assert obs.fast_processing


def test_all_systems():
    """
    ./ReadRinex.py tests/demo.10o -o r2all.nc
    ./ReadRinex.py tests/demo.10n -o r2all.nc
    """
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R / 'r2all.nc', group='OBS', autoclose=True)
# %% test reading all satellites
    for u in (None, ' ', '', ['G', 'R', 'S']):
        print('use', u)
        obs = gr.load(R/'demo.10o', use=u)
        assert obs.equals(truth)
        assert obs.fast_processing

    assert obs.position == pytest.approx([4789028.4701, 176610.0133, 4195017.031])
    try:
        assert obs.position_geodetic == approx([41.38871005, 2.11199932, 166.25085213])
    except AttributeError:  # no pymap3d
        pass
# %% test read .nc
    obs = gr.rinexobs(R / 'r2all.nc')
    assert obs.equals(truth)
# %% test write .nc
    with tempfile.TemporaryDirectory() as d:
        outfn = Path(d)/'testout.nc'
        gr.rinexobs(R/'demo.10o', outfn=Path(d)/'testout.nc')
        assert outfn.is_file() and 50000 > outfn.stat().st_size > 30000


def test_one_system():
    """./ReadRinex.py tests/demo.10o -u G -o r2G.nc
    """
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R / 'r2G.nc', group='OBS', autoclose=True)

    for u in ('G', ['G']):
        obs = gr.load(R/'demo.10o', use=u)
        assert obs.equals(truth)
        assert obs.fast_processing


def test_multi_system():
    """./ReadRinex.py tests/demo.10o -u G R -o r2GR.nc
    """
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R / 'r2GR.nc', group='OBS', autoclose=True)

    obs = gr.load(R/'demo.10o', use=('G', 'R'))
    assert obs.equals(truth)
    assert obs.fast_processing


def test_all_indicators():
    """
    ./ReadRinex.py tests/demo.10o -useindicators  -o r2all_indicators.nc
    """
    pytest.importorskip('netCDF4')

    obs = gr.load(R/'demo.10o', useindicators=True)
    truth = gr.rinexobs(R/'r2all_indicators.nc', group='OBS')

    assert obs.equals(truth)
    assert obs.fast_processing


def test_meas_indicators():
    """
    ./ReadRinex.py tests/demo.10o -useindicators -m C1 -o r2_C1_indicators.nc
    """
    pytest.importorskip('netCDF4')

    obs = gr.load(R/'demo.10o', meas='C1', useindicators=True)
    truth = gr.rinexobs(R/'r2_C1_indicators.nc', group='OBS')

    assert obs.equals(truth)
    assert obs.fast_processing


def test_meas_onesys_indicators():
    obs = gr.load(R/'demo.10o', use='G', meas='C1', useindicators=True)

    C1 = obs['C1']

    assert C1.sel(sv='G07').values == approx([22227666.76, 25342359.37])
    assert obs.fast_processing


if __name__ == '__main__':
    pytest.main(['-xrsv', __file__])
