#!/usr/bin/env python
import pytest
from pytest import approx
import xarray
import numpy as np
from pathlib import Path
from datetime import datetime
import georinex as gr
#
R = Path(__file__).parent / 'data'


def test_contents():
    """
    test specifying specific measurements (usually only a few of the thirty or so are needed)
    """
    fn = R/'demo3.10o'
    obs = gr.load(fn)
    for v in ['L1C', 'L2P', 'C1P', 'C2P', 'C1C', 'S1C', 'S1P', 'S2P']:
        assert v in obs
    assert len(obs.data_vars) == 8


def test_meas_one():
    fn = R/'demo3.10o'
    obs = gr.load(fn, meas='C1C')
    assert 'L1C' not in obs

    C1C = obs['C1C']
    assert C1C.shape == (2, 14)  # two times, 14 SVs overall for all systems in this file

    assert (C1C.sel(sv='G07') == approx([22227666.76, 25342359.37])).all()


def test_meas_two():
    """two NON-SEQUENTIAL measurements"""
    fn = R/'demo3.10o'
    obs = gr.load(fn, meas=['L1C', 'S1C'])
    assert 'L2P' not in obs

    L1C = obs['L1C']
    assert L1C.shape == (2, 14)
    assert (L1C.sel(sv='G07') == approx([118767195.32608, 133174968.81808])).all()

    S1C = obs['S1C']
    assert S1C.shape == (2, 14)

    assert (S1C.sel(sv='R23') == approx([39., 79.])).all()

    C1C = gr.load(fn, meas='C1C')
    assert not C1C.equals(L1C)


def test_meas_some_missing():
    """measurement not in some systems"""
    fn = R/'demo3.10o'
    obs = gr.load(fn, meas=['S2P'])
    assert 'L2P' not in obs

    S2P = obs['S2P']
    assert S2P.shape == (2, 14)
    assert (S2P.sel(sv='G13') == approx([40., 80.])).all()
    # satellites that don't have a measurement are NaN
    # either because they weren't visible at that time
    # or simply do not make that kind of measurement at all
    R23 = S2P.sel(sv='R23')
    assert np.isnan(R23).all()


def test_meas_all_missing():
    """measurement not in any system"""
    fn = R/'demo3.10o'
    obs = gr.load(fn, meas='nonsense')
    assert 'nonsense' not in obs

    assert len(obs.data_vars) == 0


def test_meas_wildcard():
    fn = R/'demo3.10o'
    obs = gr.load(fn, meas='C')
    assert 'L1C' not in obs
    assert 'C1P' in obs and 'C2P' in obs and 'C1C' in obs
    assert len(obs.data_vars) == 3


def test_zip():
    fn = R/'ABMF00GLP_R_20181330000_01D_30S_MO.zip'
    obs = gr.load(fn)

    assert (obs.sv.values == ['E04', 'E09', 'E12', 'E24', 'G02', 'G05', 'G06', 'G07', 'G09', 'G12', 'G13',
                              'G17', 'G19', 'G25', 'G30', 'R01', 'R02', 'R08', 'R22', 'R23', 'R24', 'S20',
                              'S31', 'S35', 'S38']).all()

    times = gr.gettime(fn)
    assert (times == [datetime(2018, 5, 13, 1, 30), datetime(2018, 5, 13, 1, 30, 30),  datetime(2018, 5, 13, 1, 31)]).all()

    hdr = gr.rinexheader(fn)
    assert hdr['t0'] <= times[0]


def test_bad_system():
    """ Z and Y are not currently used by RINEX """
    with pytest.raises(KeyError):
        gr.load(R/'demo3.10o', use='Z')

    with pytest.raises(KeyError):
        gr.load(R/'demo3.10o', use=['Z', 'Y'])


@pytest.mark.parametrize('use', ('G', ['G']))
def test_one_system(use):
    """
    ./ReadRinex.py -q tests/demo3.10o  -u G -o r3G.nc
    """
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r3G.nc', group='OBS')

    obs = gr.load(R/'demo3.10o', use=use)
    assert obs.equals(truth)

    assert obs.position == approx([4789028.4701, 176610.0133, 4195017.031])
    try:
        assert obs.position_geodetic == approx([41.38871005, 2.11199932, 166.25085213])
    except AttributeError:  # no pymap3d
        pass


def test_multi_system():
    """
    ./ReadRinex.py -q tests/demo3.10o  -u G R -o r3GR.nc
    """
    pytest.importorskip('netCDF4')

    use = ('G', 'R')

    obs = gr.load(R/'demo3.10o', use=use)
    truth = xarray.open_dataset(R/'r3GR.nc', group='OBS')

    assert obs.equals(truth)


def test_all_system():
    """
    ./ReadRinex.py -q tests/demo3.10o -o r3all.nc
    """
    pytest.importorskip('netCDF4')

    obs = gr.load(R/'demo3.10o')
    truth = gr.rinexobs(R/'r3all.nc', group='OBS')

    assert obs.equals(truth)


def tests_all_indicators():
    """
    ./ReadRinex.py -q tests/demo3.10o -useindicators -o r3all_indicators.nc
    """
    pytest.importorskip('netCDF4')

    obs = gr.load(R/'demo3.10o', useindicators=True)
    truth = gr.rinexobs(R/'r3all_indicators.nc', group='OBS')

    assert obs.equals(truth)


@pytest.mark.parametrize('fn, tname',
                         [('demo3.10o', 'GPS'),
                          ('default_time_system3.10o', 'GAL')])
def test_time_system(fn, tname):
    obs = gr.load(R/fn)
    assert obs.attrs['time_system'] == tname


if __name__ == '__main__':
    pytest.main(['-x', __file__])
