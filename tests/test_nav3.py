#!/usr/bin/env python
from pathlib import Path
import pytest
from pytest import approx
import xarray
from datetime import datetime
import georinex as gr
#
R = Path(__file__).parent / 'data'


def test_time():
    times = gr.gettime(R/'VILL00ESP_R_20181700000_01D_MN.rnx.gz')

    assert times[0] == datetime(2018, 4, 24, 8)
    assert times[-1] == datetime(2018, 6, 20, 22)


def test_tlim_past_eof():
    fn = R/'CEDA00USA_R_20182100000_01D_MN.rnx.gz'
    nav = gr.load(fn, tlim=('2018-07-29T23', '2018-07-29T23:30'))

    times = gr.to_datetime(nav.time)

    assert times == datetime(2018, 7, 29, 23)


@pytest.mark.parametrize('filename, sv, shape',
                         [('VILL00ESP_R_20181700000_01D_MN.rnx.gz', 'S36', (542, 16)),
                          ('VILL00ESP_R_20181700000_01D_MN.rnx.gz', 'G05', (7, 29)),
                          ('VILL00ESP_R_20181700000_01D_MN.rnx.gz', 'C05', (25, 28)),
                          ('VILL00ESP_R_20181700000_01D_MN.rnx.gz', 'E05', (45, 28)),
                          ('VILL00ESP_R_20181700000_01D_MN.rnx.gz', 'R05', (19, 16))],
                         ids=['SBAS', 'GPS', 'BDS', 'GAL', 'GLO'])
def test_large(filename, sv, shape):

    nav = gr.load(R / filename, use=sv[0])

    assert nav.svtype[0] == sv[0] and len(nav.svtype) == 1

    dat = nav.sel(sv=sv).dropna(how='all', dim='time').to_dataframe()
    assert dat.shape == shape

    assert dat.notnull().all().all()


@pytest.mark.parametrize('sv, size',
                         [('C05', 25), ('E05', 45), ('G05', 7), ('R05', 19), ('S36', 542)])
def test_large_all(sv, size):
    fn = R/'VILL00ESP_R_20181700000_01D_MN.rnx.gz'
    nav = gr.load(fn)
    assert sorted(nav.svtype) == ['C', 'E', 'G', 'R', 'S']

    dat = nav.sel(sv=sv).dropna(how='all', dim='time').to_dataframe()
    assert dat.shape[0] == size  # manually counted from file


def test_mixed():
    fn = R/'ELKO00USA_R_20182100000_01D_MN.rnx.gz'
    nav = gr.load(fn,
                  tlim=(datetime(2018, 7, 28, 21),
                        datetime(2018, 7, 28, 23)))

    assert isinstance(nav, xarray.Dataset)
    assert sorted(nav.svtype) == ['C', 'E', 'G', 'R']

    times = gr.to_datetime(nav.time)

    assert times.size == 15
# %% full flle test
    nav = gr.load(fn)
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

    C05 = nav.sel(sv='C06').dropna(how='all', dim='time')
    E05 = nav.sel(sv='E05').dropna(how='all', dim='time')

    assert C05.time.size == 3  # from inspection of file
    assert E05.time.size == 22  # duplications in file at same time--> take first time


@pytest.mark.parametrize('rfn, ncfn',
                         [('galileo3.15n', 'r3galileo.nc'),
                          ('demo.17n', 'r3gps.nc'),
                          ('qzss3.14n', 'r3qzss.nc'),
                          ('demo3.10n', 'r3sbas.nc')],
                         ids=['GAL', 'GPS', 'QZSS', 'SBAS'])
def test_ref(rfn, ncfn):
    """
    python ReadRinex.py tests/data/galileo3.15n -o r3galileo.nc
    python ReadRinex.py tests/data/demo.17n -o r3gps.nc
    python ReadRinex.py tests/data/qzss3.14n -o r3qzss.nc
    python ReadRinex.py tests/data/demo3.10n -o r3sbas.nc
    """
    pytest.importorskip('netCDF4')

    truth = gr.load(R/ncfn)
    nav = gr.load(R/rfn)

    assert nav.equals(truth)


def test_ionospheric_correction():
    nav = gr.load(R/"demo.17n")

    assert nav.attrs['ionospheric_corr_GPS'] == approx(
                    [1.1176e-08, -1.4901e-08, -5.9605e-08, 1.1921e-07,
                     9.8304e04, -1.1469e05, -1.9661e05, 7.2090e05])

    nav = gr.load(R/"galileo3.15n")

    assert nav.attrs['ionospheric_corr_GAL'] == approx(
                    [0.1248e+03, 0.5039, 0.2377e-01])


if __name__ == '__main__':
    pytest.main(['-x', __file__])
