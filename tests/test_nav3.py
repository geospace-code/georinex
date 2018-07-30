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


def test_qzss():
    """./ReadRinex.py -q tests/qzss3.14n -o r3qzss.nc
    """
    truth = gr.rinexnav(R/'r3qzss.nc')
    nav = gr.rinexnav(R/'qzss3.14n')
    assert nav.equals(truth)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_mixed():
    fn = R/'ELKO00USA_R_20182100000_01D_MN.rnx.gz'
    nav = gr.rinexnav(fn,
                      tlim=(datetime(2018, 7,28, 21),
                            datetime(2018, 7,28, 23)))

    assert isinstance(nav, xarray.Dataset)
    assert sorted(nav.svtype) == ['C', 'E', 'G', 'R']

    times = nav.time.values.astype('datetime64[us]').astype(datetime)

    assert times.size == 15
# %% full flle test
    nav = gr.rinexnav(fn)
    assert (nav.sv.values == ['C06', 'C07', 'C08', 'C11', 'C12', 'C14', 'C16', 'C20', 'C21',
       'C22', 'C27', 'C29', 'C30', 'E01', 'E02', 'E03', 'E04', 'E05',
       'E07', 'E08', 'E09', 'E11', 'E12', 'E14', 'E18', 'E19', 'E21',
       'E24', 'E25', 'E26', 'E27', 'E30', 'E31', 'G01', 'G02', 'G03',
       'G04', 'G05', 'G06', 'G07', 'G08', 'G09', 'G10', 'G11', 'G12',
       'G13', 'G14', 'G15', 'G16', 'G17', 'G18', 'G19', 'G20', 'G21',
       'G22', 'G23', 'G24', 'G25', 'G26', 'G27', 'G28', 'G29', 'G30',
       'G31', 'G32', 'R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07',
       'R08', 'R09', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16',
       'R17', 'R18', 'R19', 'R20', 'R21', 'R22', 'R23', 'R24']).all()

    C05 = nav.sel(sv='C06').dropna(how='all',dim='time')
    E05 = nav.sel(sv='E05').dropna(how='all',dim='time')

    assert C05.time.size == 3  # from inspection of file
    assert E05.time.size == 22  # duplications in file at same time--> take first time


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_sbas():
    """./ReadRinex.py -q tests/demo3.10n -o r3sbas.nc
    """
    truth = xarray.open_dataset(R/'r3sbas.nc', group='NAV', autoclose=True)
    nav = gr.rinexnav(R/'demo3.10n')

    assert nav.equals(truth)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_gps():
    """./ReadRinex.py -q tests/demo.17n -o r3gps.nc
    """
    truth = xarray.open_dataset(R/'r3gps.nc', group='NAV', autoclose=True)
    nav = gr.rinexnav(R/'demo.17n')

    assert nav.equals(truth)


@pytest.mark.skipif(netCDF4 is None, reason='netCDF4 required')
def test_galileo():
    """
    ./ReadRinex.py -q tests/galileo3.15n -o r3galileo.nc
    """
    truth = xarray.open_dataset(R/'r3galileo.nc', group='NAV', autoclose=True)
    nav = gr.rinexnav(R/'galileo3.15n')

    assert nav.equals(truth)


if __name__ == '__main__':
    pytest.main(['-x', __file__])
