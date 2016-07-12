#!/usr/bin/env python
from setuptools import setup
import subprocess

try:
    subprocess.call(['conda','install','--file','requirements.txt'])
except Exception as e:
    pass

#%% install
setup(name='pyrinex',
      packages=['pyrinex'],
	  description='Python RINEX reader that is very fast',
      install_requires=['pathlib2'],
	  author='Michael Hirsch',
	  url='https://github.com/scienceopen/pyrinex',
	  )
