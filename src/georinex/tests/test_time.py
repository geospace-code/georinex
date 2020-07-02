#!/usr/bin/env python
"""
test all files types with time limits
"""
import pytest
from pathlib import Path
from datetime import datetime
import numpy as np

import georinex as gr

R = Path(__file__).parent / 'data'


@pytest.mark.parametrize('fn, tlim, tref, tlen',
                         [(R/'york0440.zip',
                           ('2015-02-13T23:59', '2015-02-14T00:00'),
                           [datetime(2015, 2, 13, 23, 59, 0), datetime(2015, 2, 13, 23, 59, 30)],
                           2880),
                          (R/'CEDA00USA_R_20182100000_23H_15S_MO.rnx.gz',
                           ('2018-07-29T01:17', '2018-07-29T01:18'),
                           [datetime(2018, 7, 29, 1, 17), datetime(2018, 7, 29, 1, 17, 15),
                            datetime(2018, 7, 29, 1, 17, 45), datetime(2018, 7, 29, 1, 18)],
                           4675),
                          (R/'CEDA00USA_R_20182100000_01D_MN.rnx.gz',
                           ('2018-07-29T08', '2018-07-29T09'),
                           [datetime(2018, 7, 29, 8, 20), datetime(2018, 7, 29, 8, 50)],
                           21),
                          (R/'ceda2100.18e',
                             ('2018-07-29T11', '2018-07-29T12'),
                             [datetime(2018, 7, 29, 11, 50), datetime(2018, 7, 29, 12)],
                             21)],
                         ids=['obs2', 'obs3', 'nav3', 'nav2'])
def test_tlim(fn, tlim, tref, tlen):
    """
    Important test, be sure it's runnable on all systems
    """
    dat = gr.load(fn, tlim=tlim)

    times = gr.to_datetime(dat.time)

    assert (times == tref).all()

    if dat.rinextype == 'obs' and 2 <= dat.version < 3:
        assert dat.fast_processing

    alltimes = gr.gettime(fn)
    assert isinstance(alltimes, np.ndarray)
    assert alltimes.size == tlen

    assert np.isin(times, alltimes).size == times.size


# %% currently, interval is only for OBS2 and OBS3
@pytest.mark.parametrize('interval, expected_len', [(None, 14),
                                                    (15, 14),
                                                    (35, 8)])
def test_interval_obs3(interval, expected_len):

    obs = gr.load(R/'CEDA00USA_R_20182100000_23H_15S_MO.rnx.gz', interval=interval,
                  tlim=('2018-07-29T01:00', '2018-07-29T01:05'))

    times = gr.to_datetime(obs.time)

    assert len(times) == expected_len


@pytest.mark.parametrize('interval, expected_len', [(None, 9),
                                                    (0, 9),
                                                    (15, 9),
                                                    (35, 4)])
def test_interval_obs2(interval, expected_len):
    obs = gr.load(R/'ab430140.18o.zip', interval=interval)
    times = gr.to_datetime(obs.time)

    assert len(times) == expected_len


if __name__ == '__main__':
    pytest.main([__file__])
