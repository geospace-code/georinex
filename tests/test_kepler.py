#!/usr/bin/env python
"""
test keplerian ephemeride to ECEF conversion
"""
import pytest
import xarray
from pytest import approx
import georinex as gr
from datetime import datetime, timedelta
import numpy as np

TGPS0 = datetime(1980, 1, 6)

sv = {
    'GPSWeek': 910,
    'Toe': 410400,
    'Eccentricity': 4.27323824e-3,
    'sqrtA': 5.15353571e3,
    'Cic': 9.8720193e-8,
    'Crc': 282.28125,
    'Cis': -3.9115548e-8,
    'Crs': -132.71875,
    'Cuc': -6.60121440e-6,
    'Cus': 5.31412661e-6,
    'DeltaN': 4.3123e-9,
    'Omega0': 2.29116688,
    'omega': -0.88396725,
    'Io': 0.97477102,
    'OmegaDot': -8.025691e-9,
    'IDOT': -4.23946e-10,
    'M0': 2.24295542,
}

xref = -5.67841101e6
yref = -2.49239629e7
zref = 7.05651887e6

time = TGPS0 + timedelta(weeks=910, seconds=4.03272930e5)

dat = xarray.Dataset(sv, attrs={'svtype': 'G'},
                     coords={'time': [time]})


def test_kepler():
    x, y, z = gr.keplerian2ecef(dat)

    assert x == approx(xref, rel=1e-4)
    assert y == approx(yref, rel=1e-4)
    assert z == approx(zref, rel=1e-4)

    magerr = np.sqrt((x-xref)**2 + (y-yref)**2 + (z-zref)**2)
    print('error magnitude [meters]', magerr)


if __name__ == '__main__':
    pytest.main(['-x', __file__])
