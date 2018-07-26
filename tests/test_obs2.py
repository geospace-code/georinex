#!/usr/bin/env python
import pytest
import xarray
import tempfile
from numpy.testing import assert_allclose
from pathlib import Path
import georinex as gr
try:
    import netCDF4
except ImportError:
    netCDF4 = None
#
R = Path(__file__).parent


def test_one_sv():
    obs = gr.rinexobs(R/'rinex2onesat.10o')

    assert len(obs.sv) == 1
    assert obs.sv.item() == 'G13'


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_all_systems():
    """
    ./ReadRinex.py -q tests/demo.10o -useindicators  -o r2all.nc
    ./ReadRinex.py -q tests/demo.10n -o r2all.nc
    """
    truth = xarray.open_dataset(R / 'r2all.nc', group='OBS', autoclose=True)
# %% test reading all satellites
    for u in (None, 'm', 'all', ' ', '', ['G', 'R', 'S']):
        print('use', u)
        obs = gr.rinexobs(R/'demo.10o', use=u)
        assert obs.equals(truth)

    assert_allclose(obs.position, [4789028.4701, 176610.0133, 4195017.031])
# %% test read .nc
    obs = gr.rinexobs(R / 'r2all.nc')
    assert obs.equals(truth)
# %% test write .nc
    with tempfile.TemporaryDirectory() as d:
        obs = gr.rinexobs(R/'demo.10o', ofn=Path(d)/'testout.nc')


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_one_system():
    """./ReadRinex.py -q tests/demo.10o -u G -o r2G.nc
    """

    truth = xarray.open_dataset(R / 'r2G.nc', group='OBS', autoclose=True)

    for u in ('G', ['G']):
        obs = gr.rinexobs(R/'demo.10o', use=u)
        assert obs.equals(truth)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_multi_system():
    """./ReadRinex.py -q tests/demo.10o -u G R -o r2GR.nc
    """

    truth = xarray.open_dataset(R / 'r2GR.nc', group='OBS', autoclose=True)

    obs = gr.rinexobs(R/'demo.10o', use=('G', 'R'))
    assert obs.equals(truth)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def tests_all_indicators():
    """
    ./ReadRinex.py -q tests/demo.10o -useindicators  -o r2all_indicators.nc
    """
    obs = gr.rinexobs(R/'demo.10o', useindicators=True)
    truth = gr.rinexobs(R/'r2all_indicators.nc', group='OBS')

    assert obs.equals(truth)


if __name__ == '__main__':
    pytest.main([__file__])
