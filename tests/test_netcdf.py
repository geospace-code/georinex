#!/usr/bin/env python
import pytest
import georinex as gr
from pathlib import Path

R = Path(__file__).parent / 'data'
flist = R.glob('*.nc')

@pytest.mark.parametrize('filename', list(flist), ids=[f.name for f in flist])
def test_detect_netcdf4(filename):

    gr.load(filename)



if __name__ == '__main__':
    pytest.main(['-x', __file__])