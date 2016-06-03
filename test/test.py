#!/usr/bin/env python
"""
Self-test file, registration case
for OBS RINEX reader
"""
from pandas.io.pytables import read_hdf
from numpy.testing import assert_allclose,run_module_suite
#
from pyrinex.readRinexObs import rinexobs
from pyrinex.readRinexNav import readRinexNav

def test_obs():
    truth = read_hdf('test/demo.h5',key='OBS')
    blocks = rinexobs('test/demo.10o')
    
    assert_allclose(blocks,truth)
    
def test_nav():
    truthnav = read_hdf('test/demo.h5',key='NAV')
    testnav = readRinexNav('test/demo.10n')
    
    assert_allclose(testnav,truthnav)

if __name__ == '__main__':
    run_module_suite()