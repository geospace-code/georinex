#!/usr/bin/env python
req = ['nose','python-dateutil','pytz','numpy','pandas','numpy','pandas','h5py','xarray','matplotlib','seaborn','pathlib2']
pipreq=['tables']
# %%
import pip
try:
    import conda.cli
    conda.cli.main('install',*req)
except Exception as e:
    pip.main(['install'] +req)
pip.main(['install']+pipreq)
# %%
from setuptools import setup

#%% install
setup(name='pyrinex',
      packages=['pyrinex'],
	  description='Python RINEX reader that is very fast',
	  author='Michael Hirsch, Ph.D.',
      version='1.0.0',
	  url='https://github.com/scivision/pyrinex',
	  )
