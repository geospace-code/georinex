#!/usr/bin/env python
"""
Self-test file, registration case
for OBS RINEX reader
"""
from pandas.io.pytables import read_hdf
from numpy.testing import assert_allclose
#
from pyrinex.readRinexObs import rinexobs
from pyrinex.readRinexNav import readRinexNav

#%% do registration case
truth = read_hdf('test/demo.h5',key='OBS')

blocks = rinexobs('test/demo.10o',False,None)

assert_allclose(blocks,truth)

#%%
truthnav = read_hdf('test/demo.h5',key='NAV')
testnav = readRinexNav('test/demo.10n',False)

assert_allclose(testnav,truthnav)
