.. image:: https://travis-ci.org/scivision/pyrinex.svg?branch=master
  :target: https://travis-ci.org/scivision/pyrinex

.. image:: https://coveralls.io/repos/scivision/pyrinex/badge.svg?branch=master&service=github
  :target: https://coveralls.io/github/scivision/pyrinex?branch=master

.. image:: https://ci.appveyor.com/api/projects/status/sxxqc77q7l3669dd?svg=true
   :target: https://ci.appveyor.com/project/scivision/pyrinex

.. image:: https://img.shields.io/pypi/pyversions/pyrinex.svg
  :target: https://pypi.python.org/pypi/pyrinex
  :alt: Python versions (PyPI)

.. image::  https://img.shields.io/pypi/format/pyrinex.svg
  :target: https://pypi.python.org/pypi/pyrinex
  :alt: Distribution format (PyPI)

.. image:: https://api.codeclimate.com/v1/badges/69ce95c25db88777ed63/maintainability
   :target: https://codeclimate.com/github/scivision/pyrinex/maintainability
   :alt: Maintainability

=======
PyRinex
=======

RINEX 3 and RINEX 2 reader in Python -- reads NAV and OBS GPS RINEX data into `xarray.Dataset <http://xarray.pydata.org/en/stable/api.html#dataset>`_ for easy use in analysis and plotting.
This gives remarkable speed vs. legacy iterative methods, and allows for HPC / out-of-core operations on massive amounts of GNSS data.

Writes to NetCDF4 (subset of HDF5), with ``zlib`` compression.
This is a couple order of magnitude speedup in reading/converting RINEX data and allows filtering/processing of gigantic files too large to fit into RAM.


This module works in Python 3.5+ and 2.7.

.. contents::

Install
=======
::

  python -m pip install -e .

Usage
=====

The simplest command-line use is through the top-level ``ReadRinex.py`` script.

* Read RINEX3 or RINEX 2  Obs or Nav file: ``python ReadRinex.py myrinex.XXx``
* Read NetCDF converted RINEX data: ``python ReadRinex.py myrinex.nc`` 


You can also of course use the package as a python imported module as in the following examples.

read Obs
--------

.. code:: python

    import pyrinex as pr

    obs = pr.rinexobs('tests/demo.10o')

    obs = pr.rinexobs('tests/demo_MO.rnx')

This returns an 
`xarray.Dataset <http://xarray.pydata.org/en/stable/api.html#dataset>`_
of data within the .XXo observation file.


read Nav
--------

.. code:: python

    import pyrinex as pr

    nav = pr.rinexnav('tests/demo.10n')

    nav = pr.rinexnav('tests/demo_MN.rnx')

This returns an ``xarray.Dataset`` of the data within the RINEX 3 or RINEX 2 Navigation file.
Indexed by time x quantity



RINEX OBS reader algorithm
==========================
1. read overall OBS header (so we know what to expect in the rest of the OBS file)
2. fill the xarray.Dataset with the data by reading in blocks -- another key difference from other programs out there, instead of reading character by character, I ingest a whole time step of text at once, helping keep the processing closer to CPU cache making it much faster.
