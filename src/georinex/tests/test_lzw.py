"""
test for LZW .Z file
"""

from pathlib import Path
import pytest

import georinex as gr

R = Path(__file__).parent / "data"


def test_obs2_lzw():
    pytest.importorskip("ncompress")

    fn = R / "ac660270.18o.Z"

    obs = gr.load(fn)

    hdr = gr.rinexheader(fn)

    assert hdr["t0"] <= gr.to_datetime(obs.time[0])

    assert not obs.fast_processing
