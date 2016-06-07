#!/usr/bin/env python
from setuptools import setup
import subprocess

try:
    subprocess.call(['conda','install','--yes','--file','requirements.txt'])
except (Exception,KeyboardInterrupt) as e:
    pass

with open('README.rst','r') as f:
	long_description = f.read()
#%% install
setup(name='pyrinex',
      packages=['pyrinex'],
	  description='Python RINEX reader that is very fast',
	  long_description=long_description,
      install_requires=['pathlib2'],
	  author='Michael Hirsch',
	  url='https://github.com/scienceopen/pyrinex',
	  )
