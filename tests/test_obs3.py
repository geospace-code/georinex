#!/usr/bin/env python
from pathlib import Path
from datetime import datetime
from pytest import approx

import pytest
import georinex as gr
#
R = Path(__file__).parent / 'data'

def test_contents():
    """
    test specifying specific measurements
    (usually only a few of the thirty or so are needed)
    """
    fn = R/'demo3.10o'
    obs = gr.load(fn)
    for v in ['G_L1C', 'G_L2P', 'G_C1P', 'G_C2P', 'G_C1C', 'G_S1P', 'G_S2P']:
        assert v in obs
    for v in ['R_L1C', 'R_C1C', 'R_S1C']:
        assert v in obs

    assert len(obs.data_vars) == 13

def test_meas_one():
    fn = R/'demo3.10o'
    obs = gr.load(fn, use='G', meas='C1C')
    assert 'G_L1C' not in obs
    assert 'R_L1C' not in obs

    C1C = obs['G_C1C']
    assert C1C.shape == (2, 10)  # two times, 14 SVs overall for all systems in this file

    assert (C1C.sel(sv=7) == approx([22227666.76, 25342359.37])).all()

def test_meas_two():
    """two NON-SEQUENTIAL measurements"""
    fn = R/'demo3.10o'
    obs = gr.load(fn, use='G', meas=['L1C', 'S1P'])
    assert 'G_L2P' not in obs

    L1C = obs['G_L1C']
    assert L1C.shape == (2, 10)
    assert (L1C.sel(sv=7) == approx([118767195.32608, 133174968.81808])).all()

    S1P = obs['G_S1P']
    assert S1P.shape == (2, 10)

    assert (S1P.sel(sv=13) == approx([42., 62.])).all()

    C1C = gr.load(fn, use='G', meas='C1C')
    assert not C1C.equals(L1C)

# removed test_meas_some_missing

# Note
# Need to return an empty xarray dataset for this test

def test_meas_all_missing():
    """measurement not in any system"""
    fn = R/'demo3.10o'
    obs = gr.load(fn, meas='nonsense')
    assert 'nonsense' not in obs

    assert len(obs.data_vars) == 0

def test_meas_wildcard():
    fn = R/'demo3.10o'

    obs = gr.load(fn, use='G')
    assert 'R_L1C' not in obs
    assert 'G_C1P' in obs and 'G_C2P' in obs and 'G_C1C' in obs
    assert len(obs.data_vars) == 7

    # obs = gr.load(fn, meas='L*')
    # assert 'G_C1P' not in obs
    # assert 'G_L1C' in obs and 'G-L2P' in obs and 'R-L1C' in obs

def test_zip():
    fn = R/'ABMF00GLP_R_20181330000_01D_30S_MO.zip'
    obs = gr.load(fn)

    assert (obs.sv.values == [1,2,4,5,6,7,8,9,12,13,17,19,20,22,23,24,25,30,31,35,38]).all()

    times = gr.gettime(fn)
    assert (times == [datetime(2018, 5, 13, 1, 30), datetime(2018, 5, 13, 1, 30, 30),  datetime(2018, 5, 13, 1, 31)]).all()

    hdr = gr.rinexheader(fn)
    assert hdr['attr']['t0'] <= times[0]

# TBD
# Add more cases to include bad system

def test_bad_system():
    """ Z and Y are not currently used by RINEX """
    data = gr.load(R/'demo3.10o', use='Z')
    assert not data

    data = gr.load(R/'demo3.10o', use=['Z', 'Y'])
    assert not data

# removed test_one_system()

# removed test_multi_system()

# removed test_all system()

# removed test_all_indicators()

# Note
# Include attribute 'time_system'

@pytest.mark.parametrize('fn, tname',
                         [('demo3.10o', 'GPS'),
                          ('default_time_system3.10o', 'GAL')])
def test_time_system(fn, tname):
    obs = gr.load(R/fn)
    assert obs.attrs['time_system'] == tname


if __name__ == '__main__':
    pytest.main(['-x', __file__])
