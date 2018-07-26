#!/usr/bin/env python
import pytest
import xarray
import tempfile
from numpy.testing import assert_allclose
from pathlib import Path
import georinex as gr
#
R = Path(__file__).parent


def test_obs2_one_sv():
    obs = gr.rinexobs(R/'rinex2onesat.10o')

    assert len(obs.sv) == 1
    assert obs.sv.item() == 'G13'


def test_obs2_all_systems():
    """
    ./ReadRinex.py tests/demo.10o -o tests/test2all.nc
    ./ReadRinex.py tests/demo.10n -o tests/test2all.nc
    """
    truth = xarray.open_dataset(R/'test2all.nc', group='OBS')
# %% test reading all satellites
    for u in (None, 'm', 'all', ' ', '', ['G', 'R', 'S']):
        print('use', u)
        obs = gr.rinexobs(R/'demo.10o', use=u)
        assert obs.equals(truth)

    assert_allclose(obs.position, [4789028.4701, 176610.0133, 4195017.031])
# %% test read .nc
    obs = gr.rinexobs(R/'test2all.nc')
    assert obs.equals(truth)
# %% test write .nc
    with tempfile.TemporaryDirectory() as d:
        obs = gr.rinexobs(R/'demo.10o', ofn=Path(d)/'testout.nc')


def test_obs2_one_system():
    """./ReadRinex.py tests/demo.10o -u G -o tests/test2G.nc"""

    truth = xarray.open_dataset(R/'test2G.nc', group='OBS')

    for u in ('G', ['G']):
        obs = gr.rinexobs(R/'demo.10o', use=u)
        assert obs.equals(truth)


def test_obs2_multi_system():
    """./ReadRinex.py tests/demo.10o -u G R -o tests/test2GR.nc"""

    truth = xarray.open_dataset(R/'test2GR.nc', group='OBS')

    obs = gr.rinexobs(R/'demo.10o', use=('G', 'R'))
    assert obs.equals(truth)


if __name__ == '__main__':
    pytest.main()
