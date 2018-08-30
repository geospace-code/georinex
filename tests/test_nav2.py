#!/usr/bin/env python
import pytest
from pytest import approx
import xarray
from pathlib import Path
from datetime import datetime
import georinex as gr
import tempfile
#
R = Path(__file__).parent


def test_blank():
    fn = R/'blank.10n'
    nav = gr.load(fn)
    assert nav is None

    with tempfile.TemporaryDirectory() as outdir:
        gr.load(fn, outdir)

    times = gr.gettime(fn)
    assert times is None


def test_minimal():
    fn = R/'minimal.10n'

    nav = gr.load(fn)
    assert isinstance(nav, xarray.Dataset)

    with tempfile.TemporaryDirectory() as outdir:
        outdir = Path(outdir)
        gr.load(fn, outdir)
        outfn = (outdir / (fn.name + '.nc'))
        assert outfn.is_file()

        assert nav.equals(gr.load(outfn)), f'{outfn}  {fn}'


def test_time():
    pytest.importorskip('unlzw')

    times = gr.gettime(R/'ab422100.18n.Z').values.astype('datetime64[us]').astype(datetime)

    assert times[0] == datetime(2018, 7, 29, 1, 59, 44)
    assert times[-1] == datetime(2018, 7, 30)


def test_data():
    pytest.importorskip('unlzw')

    nav = gr.load(R/'ab422100.18n.Z')

    nav0 = nav.sel(time='2018-07-29T03:59:44').dropna(dim='sv', how='all')

    assert nav0.sv.values.tolist() == (['G18', 'G20', 'G24', 'G27'])

    G20 = nav0.sel(sv='G20')

    assert G20.to_array().values == approx([5.1321554929e-4, 6.821210263e-13, 0.,
                                            11, -74.125, 4.944134514e-09, 0.736990015, -3.810971975327e-06, 4.055858473293e-03,
                                            1.130439341068e-5, 5.153679727554e3, 14384, -2.980232238770e-8, -2.942741,
                                            -5.587935447693e-8, 9.291603197140e-01, 144.8125, 2.063514928857, -8.198555788471e-09,
                                            2.935836575092e-10, 1, 2012, 0., 2., 0., -8.381903171539e-09, 11, 9456, 4])


def test_mangled():
    fn = R/'14601736.18n'

    nav = gr.load(fn)

    times = nav.time.values.astype('datetime64[us]').astype(datetime)

    assert times == datetime(2018, 6, 22, 8)


def test_tlim():
    pytest.importorskip('unlzw')

    nav = gr.load(R/'ceda2100.18e.Z', tlim=('2018-07-29T11', '2018-07-29T12'))

    times = nav.time.values.astype('datetime64[us]').astype(datetime)

    assert (times == [datetime(2018, 7, 29, 11, 50), datetime(2018, 7, 29, 12)]).all()
# %% past end of file
    nav = gr.load(R/'p1462100.18g.Z', tlim=('2018-07-29T23:45', '2018-07-30'))

    times = nav.time.values.astype('datetime64[us]').astype(datetime)

    assert times == datetime(2018, 7, 29, 23, 45)


def test_galileo():
    pytest.importorskip('unlzw')

    nav = gr.load(R/'ceda2100.18e.Z')

    E18 = nav.sel(sv='E18').dropna(dim='time', how='all')
    assert E18.time.values.astype('datetime64[us]').astype(datetime) == datetime(2018, 7, 29, 12, 40)

    assert E18.to_array().values.squeeze() == approx([6.023218797054e-3, -2.854960712284e-11, 0.,
                                                      76, 79.53125, 3.006910964197e-09, -1.308337580849, 6.468966603279e-06,
                                                      1.659004657995e-01, 3.594905138016e-07, 5.289377120972e3,
                                                      45600, 5.243346095085e-06, 1.437602366755, 4.358589649200e-06,
                                                      8.809314114035e-01, 3.329375000000e2, 1.349316878658, -4.092313318419e-09,
                                                      -6.553844422498e-10, 517, 2.012000000000e3, 3.12, 455, 1.396983861923e-08,
                                                      1.536682248116e-08, 47064])


def test_gps():
    pytest.importorskip('unlzw')

    nav = gr.load(R/'brdc2800.15n.Z')

    times = nav.time.values.astype('datetime64[us]').astype(datetime).tolist()
    assert times[1] == datetime(2015, 10, 7, 1, 59, 28)

    nav1 = nav.sel(time='2015-10-07T01:59:28').dropna(dim='sv', how='all')

    assert nav1.to_array().values.squeeze() == approx([-0.488562509417e-04, -0.534328137292e-11, 0.,
                                                       4., 51.125, 0.408659879467e-08, -0.818212975386,
                                                       0.254809856415e-05, 0.463423598558e-02, 0.755488872528e-05,
                                                       0.515362124443e+04, 266368, 0.800937414169e-07, -0.124876382768,
                                                       0.819563865662e-07, 0.978795513619, 244., 0.737626996302,
                                                       -0.794890253227e-08, 0.621454457501e-10, 1., 1865, 0., 2.,
                                                       0., 0.558793544769e-08, 4., 265170, 4.])


def test_small():
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r2all.nc', group='NAV', autoclose=True)
    nav = gr.load(R/'demo.10n')

    assert nav.equals(truth)


if __name__ == '__main__':
    pytest.main(['-x', __file__])
