#!/usr/bin/env python
import pytest
import xarray
import tempfile
from pathlib import Path
import georinex as gr
#
rdir = Path(__file__).parent


def test_obs2_allsat():
    """
    ./ReadRinex.py tests/demo.10o -o tests/test2all.nc
    ./ReadRinex.py tests/demo.10n -o tests/test2all.nc
    """
    print('loading NetCDF4 file')
    truth = xarray.open_dataset(rdir/'test2all.nc', group='OBS')
    print('loaded.')
# %% test reading all satellites
    for u in (None, 'm', 'all', ' ', '', ['G', 'R', 'S']):
        print('use', u)
        obs = gr.rinexobs(rdir/'demo.10o', use=u)
        assert obs.equals(truth)

# %% test read .nc
    print('load NetCDF via API')
    obs = gr.rinexobs(rdir/'test2all.nc')
    print('testing equality with truth')
    assert obs.equals(truth)

# %% test write .nc
    print('testing with temp file')
    with tempfile.TemporaryDirectory() as d:
        obs = gr.rinexobs(rdir/'demo.10o', ofn=Path(d)/'testout.nc')


def test_obs2_onesat():
    """./ReadRinex.py tests/demo.10o -u G -o tests/test2G.nc"""

    truth = xarray.open_dataset(rdir/'test2G.nc', group='OBS')

    for u in ('G', ['G']):
        obs = gr.rinexobs(rdir/'demo.10o', use=u)
        assert obs.equals(truth)


def test_obs2_multisat():
    """./ReadRinex.py tests/demo.10o -u G R -o tests/test2GR.nc"""

    truth = xarray.open_dataset(rdir/'test2GR.nc', group='OBS')

    obs = gr.rinexobs(rdir/'demo.10o', use=('G', 'R'))
    assert obs.equals(truth)


if __name__ == '__main__':
    pytest.main()
