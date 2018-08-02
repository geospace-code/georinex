#!/usr/bin/env python
import pytest
import xarray
from pathlib import Path
from datetime import datetime
import georinex as gr
from numpy.testing import assert_allclose
#
R = Path(__file__).parent


def test_zip():
    fn = R/'ABMF00GLP_R_20181330000_01D_30S_MO.zip'
    obs = gr.rinexobs(fn)

    assert (obs.sv.values == ['E04', 'E09', 'E12', 'E24', 'G02', 'G05', 'G06', 'G07', 'G09', 'G12', 'G13',
                              'G17', 'G19', 'G25', 'G30', 'R01', 'R02', 'R08', 'R22', 'R23', 'R24', 'S20',
                              'S31', 'S35', 'S38']).all()

    times = gr.gettime(fn).values.astype('datetime64[us]').astype(datetime)

    assert (times == [datetime(2018, 5, 13, 1, 30), datetime(2018, 5, 13, 1, 30, 30),  datetime(2018, 5, 13, 1, 31)]).all()

    hdr = gr.rinexheader(fn)
    assert hdr['t0'] <= times[0]


def test_tlim():
    fn = R/'CEDA00USA_R_20182100000_23H_15S_MO.rnx.gz'
    obs = gr.rinexobs(fn, tlim=('2018-07-29T01:17', '2018-07-29T01:18'))

    times = obs.time.values.astype('datetime64[us]').astype(datetime)

    assert (times == [datetime(2018, 7, 29, 1, 17), datetime(2018, 7, 29, 1, 17, 15),
                      datetime(2018, 7, 29, 1, 17, 45), datetime(2018, 7, 29, 1, 18)]).all()


def test_one_system():
    """
    ./ReadRinex.py -q tests/demo3.10o  -u G -o r3G.nc
    """
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r3G.nc', group='OBS', autoclose=True)

    for u in ('G', ['G']):
        obs = gr.rinexobs(R/'demo3.10o', use=u)
        assert obs.equals(truth)

    assert_allclose(obs.position, [4789028.4701, 176610.0133, 4195017.031])


def test_multi_system():
    """
    ./ReadRinex.py -q tests/demo3.10o  -u G R -o r3GR.nc
    """
    pytest.importorskip('netCDF4')

    use = ('G', 'R')

    obs = gr.rinexobs(R/'demo3.10o', use=use)
    truth = xarray.open_dataset(R/'r3GR.nc', group='OBS', autoclose=True)

    assert obs.equals(truth)


def test_all_system():
    """
    ./ReadRinex.py -q tests/demo3.10o -o r3all.nc
    """
    pytest.importorskip('netCDF4')

    obs = gr.rinexobs(R/'demo3.10o')
    truth = gr.rinexobs(R/'r3all.nc', group='OBS')

    assert obs.equals(truth)


def tests_all_indicators():
    """
    ./ReadRinex.py -q tests/demo3.10o -useindicators -o r3all_indicators.nc
    """
    pytest.importorskip('netCDF4')

    obs = gr.rinexobs(R/'demo3.10o', useindicators=True)
    truth = gr.rinexobs(R/'r3all_indicators.nc', group='OBS')

    assert obs.equals(truth)


if __name__ == '__main__':
    pytest.main(['-x', __file__])
