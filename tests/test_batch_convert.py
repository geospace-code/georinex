#!/usr/bin/env python
import pytest
import tempfile
from pathlib import Path
import georinex as gr

R = Path(__file__).parent


def test_obs():
    pytest.importorskip('netCDF4')
    pat = '*o'

    flist = R.glob(pat)  # all OBS 2 files

    with tempfile.TemporaryDirectory() as outdir:
        gr.batch_convert(R, pat, outdir)

        for fn in flist:
            outfn = Path(outdir) / (fn.name + '.nc')
            if outfn.name.startswith('blank'):
                continue

            assert outfn.is_file(), f'{outfn}'

            truth = gr.load(fn)
            obs = gr.load(outfn)

            assert obs.equals(truth), f'{outfn}  {fn}'


def test_nav():
    pytest.importorskip('netCDF4')
    pat = '*n'

    flist = R.glob(pat)  # all OBS 2 files

    with tempfile.TemporaryDirectory() as outdir:
        gr.batch_convert(R, pat, outdir)

        for fn in flist:
            outfn = Path(outdir) / (fn.name + '.nc')
            if outfn.name.startswith('blank'):
                continue

            assert outfn.is_file(), f'{outfn}'
            assert outfn.stat().st_size > 15000, f'{outfn}'

            truth = gr.load(fn)
            nav = gr.load(outfn)

            assert nav.equals(truth), f'{outfn}  {fn}'


def test_bad():
    pat = '*o'

    with pytest.raises(TypeError):
        with tempfile.TemporaryDirectory() as baddir:
            gr.batch_convert(baddir, pat)

    with pytest.raises(FileNotFoundError):
        with tempfile.TemporaryDirectory() as outdir:
            gr.batch_convert(outdir, pat, outdir)


if __name__ == '__main__':
    pytest.main(['-xrsv', __file__])
