#!/usr/bin/env python
import pytest
import xarray
from pathlib import Path
from datetime import datetime
import georinex as gr
#
R = Path(__file__).parent


def test_time():
    times = gr.gettime(R/'ab422100.18n.Z').values.astype('datetime64[us]').astype(datetime)

    assert times[0] == datetime(2018, 7, 29, 1, 59, 44)
    assert times[-1] == datetime(2018, 7, 30)


def test_mangled():
    fn = R/'14601736.18n'

    nav = gr.load(fn)

    times = nav.time.values.astype('datetime64[us]').astype(datetime)

    assert times == datetime(2018, 6, 22, 8)


def test_tlim():
    nav = gr.load(R/'ceda2100.18e.Z', tlim=('2018-07-29T11', '2018-07-29T12'))

    times = nav.time.values.astype('datetime64[us]').astype(datetime)

    assert (times == [datetime(2018, 7, 29, 11, 50), datetime(2018, 7, 29, 12)]).all()
# %% past end of file
    nav = gr.load(R/'p1462100.18g.Z', tlim=('2018-07-29T23:45', '2018-07-30'))

    times = nav.time.values.astype('datetime64[us]').astype(datetime)

    assert times == datetime(2018, 7, 29, 23, 45)


def test_gps():
    pytest.importorskip('netCDF4')

    truth = xarray.open_dataset(R/'r2all.nc', group='NAV', autoclose=True)
    nav = gr.load(R/'demo.10n')

    assert nav.equals(truth)


if __name__ == '__main__':
    pytest.main(['-x', __file__])
