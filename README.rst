.. image:: https://travis-ci.org/scivision/pyrinex.svg?branch=master
  :target: https://travis-ci.org/scivision/pyrinex

.. image:: https://coveralls.io/repos/scivision/pyrinex/badge.svg?branch=master&service=github
  :target: https://coveralls.io/github/scivision/pyrinex?branch=master

.. image:: https://api.codeclimate.com/v1/badges/69ce95c25db88777ed63/maintainability
   :target: https://codeclimate.com/github/scivision/pyrinex/maintainability
   :alt: Maintainability

=======
PyRinex
=======

RINEX 3 and RINEX 2 reader in Python -- reads NAV and OBS GPS RINEX data into `xarray.Dataset <http://xarray.pydata.org/en/stable/api.html#dataset>`_ for easy use in analysis and plotting.
This gives remarkable speed vs. legacy iterative methods, and allows for HPC / out-of-core operations on massive amounts of GNSS data.

Writes to NetCDF4 (subset of HDF5).
This is couple order of magnitude speedup in reading and allows filtering/processing of gigantic files too large to fit into RAM.


.. contents::

Install
=======
::

  python -m pip install -e .

Usage
=====
Read RINEX3 or RINEX 2  Obs or Nav file::

  python ReadRinex.py myrinex.XXx


read Obs
--------

.. code:: python

    import pyrinex

    obsdata,header = pyrinex.rinexobs('tests/demo.10o')

This returns an 
`xarray.Dataset <http://xarray.pydata.org/en/stable/api.html#dataset>`_
of data within the .XXo observation file.


read Nav
--------

.. code:: python

    import pyrinex

    navdata = pyrinex.rinexnav('tests/demo.10n')

    navdata = pyrinex.rinexnav('tests/demo_MN.rnx')

This returns a 2-D array of the data within the RINEX 3 or RINEX 2 Navigation file.
Indexed by time x quantity



RINEX OBS reader algorithm
==========================
1. read overall OBS header (so we know what to expect in the rest of the OBS file)
2. fill the xarray.Dataset with the data by reading in blocks -- another key difference from other programs out there, instead of reading character by character I ingest a whole time step of text at once, helping keep the processing closer to CPU cache making it much faster.
