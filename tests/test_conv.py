#!/usr/bin/env python
"""
Self-test file, registration case
for OBS RINEX reader
"""
import pytest
import xarray
from pathlib import Path
import georinex as gr

rdir = Path(__file__).parent


def test_convenience():
    truth = xarray.open_dataset(rdir/'test2all.nc', group='OBS')

    obs, nav = gr.readrinex(rdir/'demo.10o')
    assert obs.equals(truth)

# %%
    print('loading NetCDF4 file')
    truth = xarray.open_dataset(rdir/'test2all.nc', group='NAV')
    obs, nav = gr.readrinex(rdir/'demo.10n')

    assert nav.equals(truth)


if __name__ == '__main__':
    pytest.main()
