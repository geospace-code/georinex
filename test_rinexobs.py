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

#%% do registration case
truth = read_hdf('test/demo.h5',key='OBS')

blocks = rinexobs('test/demo.10o',False,None)

assert_allclose(blocks,truth)
