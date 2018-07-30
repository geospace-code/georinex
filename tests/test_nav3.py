#!/usr/bin/env python
from pathlib import Path
import georinex as gr
import pytest
import xarray
from datetime import datetime
try:
    import netCDF4
except ImportError:
    netCDF4 = None
#
R = Path(__file__).parent


def test_tlim():
    fn = R/'CEDA00USA_R_20182100000_01D_MN.rnx.gz'
    nav = gr.rinexnav(fn, tlim=('2018-07-29T08', '2018-07-29T09'))

    times = nav.time.values.astype('datetime64[us]').astype(datetime)

    assert (times == [datetime(2018, 7, 29, 8, 20), datetime(2018, 7, 29, 8, 50)]).all()
# %% beyond end of file
    nav = gr.rinexnav(fn, tlim=('2018-07-29T23', '2018-07-29T23:30'))

    times = nav.time.values.astype('datetime64[us]').astype(datetime)

    assert times == datetime(2018, 7, 29, 23)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_nav3sbas():
    """./ReadRinex.py -q tests/demo3.10n -o r3sbas.nc
    """
    truth = xarray.open_dataset(R/'r3sbas.nc', group='NAV', autoclose=True)
    nav = gr.rinexnav(R/'demo3.10n')

    assert nav.equals(truth)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_nav3gps():
    """./ReadRinex.py -q tests/demo.17n -o r3gps.nc
    """
    truth = xarray.open_dataset(R/'r3gps.nc', group='NAV', autoclose=True)
    nav = gr.rinexnav(R/'demo.17n')

    assert nav.equals(truth)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_nav3galileo():
    """
    ./ReadRinex.py -q tests/galileo3.15n -o r3galileo.nc
    """
    truth = xarray.open_dataset(R/'r3galileo.nc', group='NAV', autoclose=True)
    nav = gr.rinexnav(R/'galileo3.15n')

    assert nav.equals(truth)


if __name__ == '__main__':
    pytest.main(['-x', __file__])
