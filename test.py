#!/usr/bin/env python
"""
Self-test file, registration case
for OBS RINEX reader
Michael Hirsch
"""
from pandas.io.pytables import read_hdf
from numpy.testing import assert_allclose
#
from RinexObsReader import rinexobs
from RinexNavReader import readRINEXnav

#%% do registration case
truth = read_hdf('test/demo.h5',key='OBS')

blocks = rinexobs('test/demo.10o',False,None)

assert_allclose(blocks,truth)

#%%
truthnav = read_hdf('test/demo.h5',key='NAV')
testnav = readRINEXnav('test/demo.10n',False)

assert_allclose(testnav,truthnav)
