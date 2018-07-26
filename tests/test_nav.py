#!/usr/bin/env python
import pytest
import xarray
from pathlib import Path
import georinex as gr
try:
    import netCDF4
except ImportError:
    netCDF4 = None
#
R = Path(__file__).parent


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_nav2():
    truth = xarray.open_dataset(R/'r2all.nc', group='NAV', autoclose=True)
    nav = gr.rinexnav(R/'demo.10n')

    assert nav.equals(truth)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_nav3sbas():
    """./ReadRinex.py -q tests/demo3.10n -o r3sbas.nc
    """
    truth = xarray.open_dataset(R/'r3sbas.nc', group='NAV', autoclose=True)
    nav = gr.rinexnav(R/'demo3.10n')

    assert nav.equals(truth)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_nav3gps():
    """./ReadRinex.py -qtests/demo.17n -o r3gps.nc
    """
    truth = xarray.open_dataset(R/'r3gps.nc', group='NAV', autoclose=True)
    nav = gr.rinexnav(R/'demo.17n')

    assert nav.equals(truth)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_nav3galileo():
    """
    ./ReadRinex.py tests/galileo3.15n -o r3galileo.nc
    """
    truth = xarray.open_dataset(R/'r3galileo.nc', group='NAV', autoclose=True)
    nav = gr.rinexnav(R/'galileo3.15n')

    assert nav.equals(truth)


if __name__ == '__main__':
    pytest.main([__file__])
