#!/usr/bin/env python
"""
test console script
"""
import pytest
import subprocess
from pathlib import Path
import tempfile

R = Path(__file__).parent


def test_convenience():
    subprocess.check_call(['ReadRinex', str(R / 'demo.10o')])


def test_time():
    subprocess.check_call(['TimeRinex', str(R)])


def test_batch_convert():
    pytest.importorskip('netCDF4')

    pat = '*.o'

    flist = R.glob(pat)  # all OBS 2 files

    with tempfile.TemporaryDirectory() as outdir:
        subprocess.check_call(['rnx2hdf5', str(R), '*o', '-o', outdir])

        for fn in flist:
            outfn = Path(outdir) / (fn.name + '.nc')
            assert outfn.is_file()
            assert outfn.stat().st_size > 30000, f'{outfn}'


if __name__ == '__main__':
    pytest.main(['-x', __file__])
