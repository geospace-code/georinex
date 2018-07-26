#!/usr/bin/env python
import pytest
import xarray
from pathlib import Path
import georinex as gr
import numpy as np
from numpy.testing import assert_allclose
try:
    import netCDF4
except ImportError:
    netCDF4 = None
#
R = Path(__file__).parent


def test_zip():
    obs = gr.rinexobs(R/'ABMF00GLP_R_20181330000_01D_30S_MO.zip')

    assert (obs.sv.values == ['E04', 'E09', 'E12', 'E24', 'G02', 'G05', 'G06', 'G07', 'G09', 'G12', 'G13',
                              'G17', 'G19', 'G25', 'G30', 'R01', 'R02', 'R08', 'R22', 'R23', 'R24', 'S20',
                              'S31', 'S35', 'S38']).all()

    assert (obs.time.values == np.array(
        ['2018-05-13T01:30:00.000000000', '2018-05-13T01:30:30.000000000',  '2018-05-13T01:31:00.000000000'],
        dtype='datetime64[ns]')).all()


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_one_system():
    """
    ./ReadRinex.py -q tests/demo3.10o  -u G -o r3G.nc
    """

    truth = xarray.open_dataset(R/'r3G.nc', group='OBS', autoclose=True)

    for u in ('G', ['G']):
        obs = gr.rinexobs(R/'demo3.10o', use=u)
        assert obs.equals(truth)

    assert_allclose(obs.position, [4789028.4701, 176610.0133, 4195017.031])


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_multi_system():
    """
    ./ReadRinex.py -q tests/demo3.10o  -u G R -o r3GR.nc
    """
    use = ('G', 'R')

    obs = gr.rinexobs(R/'demo3.10o', use=use)
    truth = xarray.open_dataset(R/'r3GR.nc', group='OBS', autoclose=True)

    assert obs.equals(truth)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_all_system():
    """
    ./ReadRinex.py -q tests/demo3.10o -o r3all.nc
    """

    obs = gr.rinexobs(R/'demo3.10o')
    truth = gr.rinexobs(R/'r3all.nc', group='OBS')

    assert obs.equals(truth)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def tests_all_indicators():
    """
    ./ReadRinex.py -q tests/demo3.10o -useindicators -o r3all_indicators.nc
    """

    obs = gr.rinexobs(R/'demo3.10o', useindicators=True)
    truth = gr.rinexobs(R/'r3all_indicators.nc', group='OBS')

    assert obs.equals(truth)


if __name__ == '__main__':
    pytest.main([__file__])
