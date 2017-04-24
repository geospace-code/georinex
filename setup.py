#!/usr/bin/env python
req = ['nose','numpy','pandas','xarray','matplotlib','seaborn','pathlib2']
# %%
import pip
try:
    import conda.cli
    conda.cli.main('install',*req)
except Exception as e:
    pip.main(['install'] +req)
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
