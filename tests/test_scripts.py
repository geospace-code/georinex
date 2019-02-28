#!/usr/bin/env python
"""
test console script
"""
import pytest
import subprocess
from pathlib import Path

R = Path(__file__).parent / 'data'


def test_convenience():
    subprocess.check_call(['ReadRinex', str(R / 'demo.10o')])


def test_time():
    subprocess.check_call(['TimeRinex', str(R)])


# %% convert all OBS 2 files to NetCDF4
pat = '*.*o'
flist = list(R.glob(pat))
assert len(flist) > 0


@pytest.mark.parametrize('filename', flist, ids=[f.name for f in flist])
def test_batch_convert(tmp_path, filename):
    pytest.importorskip('netCDF4')

    if filename.name.startswith('blank'):
        return  # this file has no contents, hence nothing to convert to NetCDF4

    outdir = tmp_path
    subprocess.check_call(['rnx2hdf5', str(R), '*o', '-o', str(outdir)])

    outfn = outdir / (filename.name + '.nc')
    assert outfn.is_file()
    assert outfn.stat().st_size > 30000, f'{outfn}'


if __name__ == '__main__':
    pytest.main(['-x', __file__])
