#!/usr/bin/env python
import pytest
from pathlib import Path
import georinex as gr

R = Path(__file__).parent / 'data'


flist = list(R.glob('*.*o')) + list(R.glob('*.*n'))
assert len(flist) > 0


@pytest.mark.parametrize('filename', flist, ids=[f.name for f in flist])
def test_batch_convert_rinex2(tmp_path, filename):
    pytest.importorskip('netCDF4')

    outdir = tmp_path
    gr.batch_convert(R, filename.name, outdir)

    outfn = outdir / (filename.name + '.nc')
    if outfn.name.startswith('blank'):
        return  # blank files do not convert

    assert outfn.is_file(), f'{outfn}'
    assert outfn.stat().st_size > 15000, f'{outfn}'

    truth = gr.load(filename)
    dat = gr.load(outfn)

    assert dat.equals(truth), f'{outfn}  {filename}'


def test_bad(tmp_path):
    pat = '*o'

    with pytest.raises(TypeError):
        gr.batch_convert(tmp_path, pat)


if __name__ == '__main__':
    pytest.main(['-xrsv', __file__])
