#!/usr/bin/env python
install_requires = ['numpy','numpy','xarray','netcdf4','pathlib2']
tests_require=['pytest','nose','coveralls']
# %%
from setuptools import setup,find_packages
setup(name='pyrinex',
      packages=find_packages(),
	  description='Python RINEX reader that is very fast',
	  long_description=open('README.rst').read(),
	  author='Michael Hirsch, Ph.D.',
      version='1.2.1',
	  url='https://github.com/scivision/pyrinex',
	  install_requires=install_requires,
	  tests_require=tests_require,
      python_requires='>=2.7',
      extras_require={'plot':['matplotlib','seaborn','pymap3d'],
                       'tests':tests_require,},
      classifiers=[
      'Development Status :: 5 - Production/Stable',
      'Environment :: Console',
      'Intended Audience :: Science/Research',
      'Operating System :: OS Independent',
      'Programming Language :: Python :: 3',
      'Topic :: Scientific/Engineering :: Atmospheric Science',
      ],
      include_package_data=True,
	  )
