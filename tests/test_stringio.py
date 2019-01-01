#!/usr/bin/env python
import pytest
from pytest import approx
from pathlib import Path
import georinex as gr
import io
from datetime import datetime

R = Path(__file__).parent / 'data'


def test_nav3():
    fn = R / 'minimal3.10n'
    with fn.open('r') as f:
        txt = f.read()

    with io.StringIO(txt) as f:
        rtype = gr.rinextype(f)
        assert rtype == 'nav'

        times = gr.gettime(f).values.astype('datetime64[us]').astype(datetime).item()
        nav = gr.load(f)

        nav3 = gr.rinexnav3(f)

    assert times == datetime(2010, 10, 18, 0, 1, 4)
    assert nav.equals(nav3), 'NAV3 StringIO failure'
    assert nav.equals(gr.load(fn)), 'NAV3 StringIO failure'


def test_nav2():
    fn = R / 'minimal.10n'
    with fn.open('r') as f:
        txt = f.read()

    with io.StringIO(txt) as f:
        rtype = gr.rinextype(f)
        assert rtype == 'nav'

        times = gr.gettime(f).values.astype('datetime64[us]').astype(datetime).item()
        nav = gr.load(f)

        nav2 = gr.rinexnav2(f)

    assert times == datetime(1999, 9, 2, 19)
    assert nav.equals(nav2), 'NAV2 StringIO failure'
    assert nav.equals(gr.load(fn)), 'NAV2 StringIO failure'


def test_obs2():
    fn = R / 'minimal.10o'
    with fn.open('r') as f:
        txt = f.read()

    with io.StringIO(txt) as f:
        rtype = gr.rinextype(f)
        assert rtype == 'obs'

        times = gr.gettime(f).values.astype('datetime64[us]').astype(datetime).item()
        obs = gr.load(f)

        obs2 = gr.rinexobs2(f)

    assert times == datetime(2010, 3, 5, 0, 0, 30)
    assert obs.equals(obs2), 'OBS2 StringIO failure'
    assert obs.equals(gr.load(fn)), 'OBS2 StringIO failure'


def test_obs3():
    fn = R / 'minimal3.10o'
    with fn.open('r') as f:
        txt = f.read()

    with io.StringIO(txt) as f:
        rtype = gr.rinextype(f)
        assert rtype == 'obs'

        times = gr.gettime(f).values.astype('datetime64[us]').astype(datetime).item()
        obs = gr.load(f)

        obs3 = gr.rinexobs3(f)

    assert times == datetime(2010, 3, 5, 0, 0, 30)
    assert obs.equals(obs3), 'OBS3 StringIO failure'
    assert obs.equals(gr.load(fn)), 'OBS3 StringIO failure'


def test_locs():
    locs = gr.getlocations(R / 'demo.10o')

    assert locs.loc['demo.10o'].values == approx([41.3887, 2.112, 30])


if __name__ == '__main__':
    pytest.main(['-x', __file__])
