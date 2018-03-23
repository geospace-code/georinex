#!/usr/bin/env python
install_requires = ['numpy','xarray','netcdf4','pathlib2']
tests_require=['pytest','nose','coveralls']
# %%
from setuptools import setup,find_packages

setup(name='pyrinex',
      packages=find_packages(),
	  description='Python RINEX 2/3 NAV/OBS reader that is very fast',
	  long_description=open('README.rst').read(),
	  author='Michael Hirsch, Ph.D.',
      version='1.2.5',
	  url='https://github.com/scivision/pyrinex',
	  install_requires=install_requires,
	  tests_require=tests_require,
      python_requires='>=2.7',
      extras_require={'plot':['matplotlib','seaborn','pymap3d'],
                       'tests':tests_require,},
      classifiers=[
      'Development Status :: 4 - Beta',
      'Environment :: Console',
      'Intended Audience :: Science/Research',
      'Operating System :: OS Independent',
      'Programming Language :: Python :: 3',
      'Topic :: Scientific/Engineering :: Atmospheric Science',
      ],
      script=['ReadRinex.py'],
      include_package_data=True,
	  )
