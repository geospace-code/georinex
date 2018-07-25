#!/usr/bin/env python
import pytest
import xarray
from pathlib import Path
import georinex as gr
#
rdir = Path(__file__).parent


def test_nav2():
    truth = xarray.open_dataset(rdir/'test2all.nc', group='NAV')
    nav = gr.rinexnav(rdir/'demo.10n')

    assert nav.equals(truth)


def test_nav3sbas():
    """./ReadRinex.py tests/demo3.10n -o tests/test3sbas.nc"""
    truth = xarray.open_dataset(rdir/'test3sbas.nc', group='NAV')
    nav = gr.rinexnav(rdir/'demo3.10n')

    assert nav.equals(truth)


def test_nav3gps():
    """./ReadRinex.py tests/demo.17n -o tests/test3gps.nc"""
    truth = xarray.open_dataset(rdir/'test3gps.nc', group='NAV')
    nav = gr.rinexnav(rdir/'demo.17n')

    assert nav.equals(truth)


def test_nav3galileo():
    """
    ./ReadRinex.py tests/galileo3.15n -o tests/test3galileo.nc
    """
    truth = xarray.open_dataset(rdir/'test3galileo.nc', group='NAV')
    nav = gr.rinexnav(rdir/'galileo3.15n')

    assert nav.equals(truth)


if __name__ == '__main__':
    pytest.main()
