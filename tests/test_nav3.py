#!/usr/bin/env python
from pathlib import Path
import georinex as gr
import pytest
import xarray
import tempfile
from datetime import datetime
#
R = Path(__file__).parent


def test_blank():
    fn = R/'blank3.10n'
    nav = gr.load(fn)
    assert nav is None

    with tempfile.TemporaryDirectory() as outdir:
        gr.load(fn, outdir)

    times = gr.gettime(fn)
    assert times is None


def test_minimal():
    fn = R/'minimal3.10n'

    nav = gr.load(fn)
    assert isinstance(nav, xarray.Dataset)

    with tempfile.TemporaryDirectory() as outdir:
        outdir = Path(outdir)
        gr.load(fn, outdir)
        outfn = (outdir / (fn.name + '.nc'))
        assert outfn.is_file()

        assert nav.equals(gr.load(outfn)), f'{outfn}  {fn}'


def test_time():
    times = gr.gettime(R/'VILL00ESP_R_20181700000_01D_MN.rnx.gz').values.astype('datetime64[us]').astype(datetime)

    assert times[0] == datetime(2018, 4, 24, 8)
    assert times[-1] == datetime(2018, 6, 20, 22)


def test_tlim():
    fn = R/'CEDA00USA_R_20182100000_01D_MN.rnx.gz'
    nav = gr.load(fn, tlim=('2018-07-29T08', '2018-07-29T09'))

    times = nav.time.values.astype('datetime64[us]').astype(datetime)

    assert (times == [datetime(2018, 7, 29, 8, 20), datetime(2018, 7, 29, 8, 50)]).all()
# %% beyond end of file
    nav = gr.load(fn, tlim=('2018-07-29T23', '2018-07-29T23:30'))

    times = nav.time.values.astype('datetime64[us]').astype(datetime)

    assert times == datetime(2018, 7, 29, 23)


def test_qzss():
    """./ReadRinex.py -q tests/qzss3.14n -o r3qzss.nc
    """
    pytest.importorskip('netCDF4')

    truth = gr.load(R/'r3qzss.nc')
    nav = gr.load(R/'qzss3.14n')
    assert nav.equals(truth)


def test_large_galileo():
    fn = R/'VILL00ESP_R_20181700000_01D_MN.rnx.gz'
    nav = gr.load(fn, use='E')

    assert nav.svtype[0] == 'E' and len(nav.svtype) == 1

    E05 = nav.sel(sv='E05').dropna(how='all', dim='time').to_dataframe()
    assert E05.shape[0] == 45  # manually counted from file
    assert E05.shape[1] == 28  # by Galileo NAV3 def'n

    assert E05.notnull().all().all()


def test_large_beidou():
    fn = R/'VILL00ESP_R_20181700000_01D_MN.rnx.gz'
    nav = gr.load(fn, use='C')

    assert nav.svtype[0] == 'C' and len(nav.svtype) == 1

    C05 = nav.sel(sv='C05').dropna(how='all', dim='time').to_dataframe()
    assert C05.shape[0] == 25  # manually counted from file
    assert C05.shape[1] == 29  # by Beidou NAV3 def'n

    assert C05.notnull().all().all()


def test_large_gps():
    fn = R/'VILL00ESP_R_20181700000_01D_MN.rnx.gz'
    nav = gr.load(fn, use='G')

    assert nav.svtype[0] == 'G' and len(nav.svtype) == 1

    G05 = nav.sel(sv='G05').dropna(how='all', dim='time').to_dataframe()
    assert G05.shape[0] == 7  # manually counted from file
    assert G05.shape[1] == 30  # by GPS NAV3 def'n

    assert G05.notnull().all().all()


def test_large_sbas():
    fn = R/'VILL00ESP_R_20181700000_01D_MN.rnx.gz'
    nav = gr.load(fn, use='S')

    assert nav.svtype[0] == 'S' and len(nav.svtype) == 1

    S36 = nav.sel(sv='S36').dropna(how='all', dim='time').to_dataframe()
    assert S36.shape[0] == 542  # manually counted from file
    assert S36.shape[1] == 16  # by SBAS NAV3 def'n

    assert S36.notnull().all().all()


def test_large_glonass():
    fn = R/'VILL00ESP_R_20181700000_01D_MN.rnx.gz'
    nav = gr.load(fn, use='R')

    assert nav.svtype[0] == 'R' and len(nav.svtype) == 1

    R05 = nav.sel(sv='R05').dropna(how='all', dim='time').to_dataframe()
    assert R05.shape[0] == 19  # manually counted from file
    assert R05.shape[1] == 16  # by GLONASS NAV3 def'n

    assert R05.notnull().all().all()


def test_large():
    fn = R/'VILL00ESP_R_20181700000_01D_MN.rnx.gz'
    nav = gr.load(fn)
    assert sorted(nav.svtype) == ['C', 'E', 'G', 'R', 'S']

    C05 = nav.sel(sv='C05').dropna(how='all', dim='time').to_dataframe()
    assert C05.shape[0] == 25  # manually counted from file

    E05 = nav.sel(sv='E05').dropna(how='all', dim='time').to_dataframe()
    assert E05.shape[0] == 45  # manually counted from file

    G05 = nav.sel(sv='G05').dropna(how='all', dim='time').to_dataframe()
    assert G05.shape[0] == 7  # manually counted from file

    R05 = nav.sel(sv='R05').dropna(how='all', dim='time').to_dataframe()
    assert R05.shape[0] == 19

    S36 = nav.sel(sv='S36').dropna(how='all', dim='time').to_dataframe()
    assert S36.shape[0] == 542  # manually counted from file


def test_mixed():
    fn = R/'ELKO00USA_R_20182100000_01D_MN.rnx.gz'
    nav = gr.load(fn,
                  tlim=(datetime(2018, 7, 28, 21),
                        datetime(2018, 7, 28, 23)))

    assert isinstance(nav, xarray.Dataset)
    assert sorted(nav.svtype) == ['C', 'E', 'G', 'R']

    times = nav.time.values.astype('datetime64[us]').astype(datetime)

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


def test_sbas():
    """./ReadRinex.py -q tests/demo3.10n -o r3sbas.nc
    """
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r3sbas.nc', group='NAV', autoclose=True)
    nav = gr.load(R/'demo3.10n')

    assert nav.equals(truth)


def test_gps():
    """./ReadRinex.py -q tests/demo.17n -o r3gps.nc
    """
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r3gps.nc', group='NAV', autoclose=True)
    nav = gr.load(R/'demo.17n')

    assert nav.equals(truth)


def test_galileo():
    """
    ./ReadRinex.py -q tests/galileo3.15n -o r3galileo.nc
    """
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r3galileo.nc', group='NAV', autoclose=True)
    nav = gr.load(R/'galileo3.15n')

    assert nav.equals(truth)


if __name__ == '__main__':
    pytest.main(['-x', __file__])
