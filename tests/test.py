#!/usr/bin/env python
"""
Self-test file, registration case
for OBS RINEX reader
"""
from pathlib import Path
from pandas.io.pytables import read_hdf
from numpy.testing import assert_allclose,run_module_suite
#
from pyrinex import rinexobs, readRinexNav

rdir=Path(__file__).parents[1]

def test_obs():
    truth = read_hdf(str(rdir/'tests/demo.h5'),key='OBS')
    blocks = rinexobs(str(rdir/'tests/demo.10o'))
    
    assert_allclose(blocks,truth)
    
def test_nav():
    truthnav = read_hdf(str(rdir/'tests/demo.h5'),key='NAV')
    testnav = readRinexNav(str(rdir/'tests/demo.10n'))
    
    assert_allclose(testnav,truthnav)

if __name__ == '__main__':
    run_module_suite()
