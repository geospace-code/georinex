#!/usr/bin/env python
"""
Self-test file, registration case
for OBS RINEX reader
"""
import xarray
from pyrinex import Path
from numpy.testing import  run_module_suite
#
from pyrinex import rinexobs, rinexnav
#
rdir=Path(__file__).parent


def test_obs2():
    """./ReadRinex.py tests/demo.10o -o tests/test.nc"""

    truth = xarray.open_dataset(rdir/'test.nc', group='OBS')
    obs = rinexobs(rdir/'demo.10o')

    assert obs.equals(truth)


def test_nav2():
    """./ReadRinex.py tests/demo.10n -o tests/test.nc"""

    truth = xarray.open_dataset(rdir/'test.nc', group='NAV')
    nav = rinexnav(rdir/'demo.10n')

    assert nav.equals(truth)


def test_obs3():
    """./ReadRinex.py tests/demo3.10o -o tests/test3.nc"""

    truth = xarray.open_dataset(rdir/'test3.nc', group='OBS')
    obs = rinexobs(rdir/'demo3.10o', use='G')

    assert obs.equals(truth)


def test_nav3sbas():
    """./ReadRinex.py tests/demo3.10n -o tests/test3sbas.nc"""
    truth = xarray.open_dataset(rdir/'test3sbas.nc', group='NAV')
    nav = rinexnav(rdir/'demo3.10n')

    assert nav.equals(truth)

def test_nav3gps():
    """./ReadRinex.py tests/demo.17n -o tests/test3gps.nc"""
    truth = xarray.open_dataset(rdir/'test3gps.nc', group='NAV')
    nav = rinexnav(rdir/'demo.17n')

    assert nav.equals(truth)


if __name__ == '__main__':
    run_module_suite()
