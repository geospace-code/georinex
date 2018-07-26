#!/usr/bin/env python
import pytest
import xarray
from pathlib import Path
import georinex as gr
from numpy.testing import assert_allclose
#
rdir = Path(__file__).parent


def test_obs3_onesat():
    """
    ./ReadRinex.py tests/demo3.10o  -u G -o tests/test3G.nc
    """

    truth = xarray.open_dataset(rdir/'test3G.nc', group='OBS')

    for u in ('G', ['G']):
        obs = gr.rinexobs(rdir/'demo3.10o', use=u)
        assert obs.equals(truth)

    assert_allclose(obs.position, [4789028.4701, 176610.0133, 4195017.031])


def test_obs3_multisat():
    """
    ./ReadRinex.py tests/demo3.10o  -u G R -o tests/test3GR.nc
    """
    use = ('G', 'R')

    obs = gr.rinexobs(rdir/'demo3.10o', use=use)
    truth = xarray.open_dataset(rdir/'test3GR.nc', group='OBS')

    assert obs.equals(truth)


def test_obs3_allsat():
    """
    ./ReadRinex.py tests/demo3.10o -o tests/test3all.nc
    """

    obs = gr.rinexobs(rdir/'demo3.10o')
    truth = gr.rinexobs(rdir/'test3all.nc', group='OBS')

    assert obs.equals(truth)


if __name__ == '__main__':
    pytest.main()
