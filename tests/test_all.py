#!/usr/bin/env python
"""
Self-test file, registration case
for OBS RINEX reader
"""
import xarray
from pyrinex import Path
from numpy.testing import assert_allclose, run_module_suite
#
from pyrinex import rinexobs, rinexnav

rdir=Path(__file__).parent
ofn3sbas = rdir/'test3sbas.nc'
ofn3gps = rdir/'test3gps.nc'

def test_obs2():
    """./ReadRinex.py tests/demo.10o -o tests/test.nc"""

    truth = xarray.open_dataarray(rdir/'test.nc', group='OBS')

    blocks,hdr = rinexobs(rdir/'demo.10o')

    assert_allclose(blocks,truth)


def test_nav2():
    """./ReadRinex.py tests/demo.10n -o tests/test.nc"""

    truth = xarray.open_dataset(rdir/'test.nc', group='NAV')
    testnav = rinexnav(rdir/'demo.10n')

    assert testnav.equals(truth)


def test_nav3sbas():

    truth = xarray.open_dataarray(str(ofn3sbas), group='NAV')
    testnav = rinexnav(rdir/'demo3.10n')

    assert_allclose(testnav,truth)

def test_nav3gps():

    truth = xarray.open_dataarray(str(ofn3gps), group='NAV')
    testnav = rinexnav(rdir/'demo.17n')

    assert_allclose(testnav,truth)


if __name__ == '__main__':
    run_module_suite()
