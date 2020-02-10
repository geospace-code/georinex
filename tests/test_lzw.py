#!/usr/bin/env python
"""
test for LZW .Z file
"""
from pathlib import Path
import pytest

import georinex as gr

R = Path(__file__).parent / 'data'


def test_obs2():
    pytest.importorskip('unlzw3')

    fn = R / 'ac660270.18o.Z'

    obs = gr.load(fn)

    hdr = gr.rinexheader(fn)

    assert hdr['t0'] <= gr.to_datetime(obs.time[0])

    assert not obs.fast_processing


if __name__ == '__main__':
    pytest.main([__file__])
