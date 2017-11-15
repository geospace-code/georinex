#!/usr/bin/env python
"""
Self-test file, registration case
for OBS RINEX reader
"""
import xarray
from pyrinex import Path
from numpy.testing import assert_allclose,run_module_suite
#
from pyrinex import rinexobs, rinexnav

rdir=Path(__file__).parents[1]

def test_obs():

    truth = xarray.open_dataarray(str(rdir/'tests/testobs.nc'))

    blocks,hdr = rinexobs(rdir/'tests/demo.10o')

    assert_allclose(blocks,truth)

def test_nav():

    truth = xarray.open_dataarray(str(rdir/'tests/testnav.nc'))
    testnav = rinexnav(rdir/'tests/demo.10n')

    assert_allclose(testnav,truth)

if __name__ == '__main__':
    run_module_suite()
