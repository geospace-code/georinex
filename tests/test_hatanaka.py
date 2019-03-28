#!/usr/bin/env python
import pytest
from pathlib import Path
from datetime import datetime

import georinex as gr

R = Path(__file__).parent / 'data'


def test_obs2():
    fn = R / 'york0440.15d'

    info = gr.rinexinfo(fn)
    assert int(info['version']) == 1

    if not gr.crxexe():
        pytest.skip(f'crx2rnx not found')

    obs = gr.load(fn, tlim=('2015-02-13T23:00', '2015-02-13T23:01'))

    assert obs.time.size == 3
    assert obs.sv.size == 9
    assert obs['S1'].values[0, :3] == pytest.approx([44., 41., 51.])


@pytest.mark.timeout(30)
def test_obs3_gz():

    fn = R / 'CEBR00ESP_R_20182000000_01D_30S_MO.crx.gz'

    info = gr.rinexinfo(fn)
    assert int(info['version']) == 3

    if not gr.crxexe():
        pytest.skip(f'crx2rnx not found')
# %% full file
    obs = gr.load(fn, tlim=('2018-07-19T01', '2018-07-19T01:10'))

    assert (obs.sv.values == ['C05', 'C10', 'C14', 'C22', 'C31', 'E01', 'E04', 'E09', 'E11',
                              'E19', 'E21', 'E31', 'G02', 'G05', 'G07', 'G13', 'G15', 'G21',
                              'G24', 'G28', 'G30', 'R03', 'R04', 'R05', 'R13', 'R14', 'R15',
                              'R16', 'R21', 'S20', 'S23', 'S25', 'S47', 'S48']).all()

    times = gr.to_datetime(obs.time)

    assert times[0] == datetime(2018, 7, 19, 1)
    assert times[-1] == datetime(2018, 7, 19, 1, 10)


@pytest.mark.timeout(30)
def test_obs3():
    if not gr.crxexe():
        pytest.skip(f'crx2rnx not found')

    fn = R / 'P43300USA_R_20190012056_17M_15S_MO.crx'

    info = gr.rinexinfo(fn)

    assert int(info['version']) == 3
# %% full file
    obs = gr.load(fn, tlim=('2019-01-01', '2019-01-01T20:57'))

    assert (obs.sv.values == ['C08', 'C19', 'C20', 'C22', 'C32', 'C36', 'C37', 'E02', 'E03',
                              'E05', 'E08', 'E24', 'E25', 'G01', 'G03', 'G06', 'G09', 'G14',
                              'G16', 'G22', 'G23', 'G26', 'G31', 'R01', 'R02', 'R08', 'R10',
                              'R11', 'R12', 'R17', 'S31', 'S33', 'S35', 'S38']).all()

    times = gr.to_datetime(obs.time)

    assert times[0] == datetime(2019, 1, 1, 20, 56, 45)
    assert times[-1] == datetime(2019, 1, 1, 20, 57)


if __name__ == '__main__':
    pytest.main(['-x', __file__])
