#!/usr/bin/env python
import pytest
from pathlib import Path
import georinex as gr

R = Path(__file__).parent / 'data'


def test_obs(tmp_path):
    pytest.importorskip('netCDF4')
    pat = '*o'

    flist = R.glob(pat)  # all OBS 2 files

    outdir = tmp_path
    gr.batch_convert(R, pat, outdir)

    for fn in flist:
        outfn = outdir / (fn.name + '.nc')
        if outfn.name.startswith('blank'):
            continue

        assert outfn.is_file(), f'{outfn}'

        truth = gr.load(fn)
        obs = gr.load(outfn)

        assert obs.equals(truth), f'{outfn}  {fn}'


def test_nav(tmp_path):
    pytest.importorskip('netCDF4')
    pat = '*n'

    flist = R.glob(pat)  # all OBS 2 files

    outdir = tmp_path
    gr.batch_convert(R, pat, outdir)

    for fn in flist:
        outfn = outdir / (fn.name + '.nc')
        if outfn.name.startswith('blank'):
            continue

        assert outfn.is_file(), f'{outfn}'
        assert outfn.stat().st_size > 15000, f'{outfn}'

        truth = gr.load(fn)
        nav = gr.load(outfn)

        assert nav.equals(truth), f'{outfn}  {fn}'


def test_bad(tmp_path):
    pat = '*o'

    with pytest.raises(TypeError):
        outdir = tmp_path
        gr.batch_convert(outdir, pat)

    with pytest.raises(FileNotFoundError):
        outdir = tmp_path
        gr.batch_convert(outdir, pat, outdir)


if __name__ == '__main__':
    pytest.main(['-xrsv', __file__])
