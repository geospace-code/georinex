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

Another key advantage of PyRinex is the Xarray base class, that allows all the database-like indexing power of Pandas to be unleashed. 


PyRinex works in Python >= 3.5.

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
Each example assumes you have first done:

.. code:: python

    import pyrinex as pr

read Rinex
------------
This convenience function reads any possible Rinex 2/3 OBS/NAV or .nc file:


.. code:: python

    obs,nav = pr.readrinex('tests/demo.10o')


read Obs
--------
If you desire to specifically read a RINEX 2 or 3 OBS file:

.. code:: python

    obs = pr.rinexobs('tests/demo_MO.rnx')

This returns an
`xarray.Dataset <http://xarray.pydata.org/en/stable/api.html#dataset>`_
of data within the .XXo observation file.

`NaN` is used as a filler value, so the commands typically end with `.dropna(dim='time',how='all')` to eliminate the non-observable data vs time.
As per pg. 15-20 of RINEX 3.03 `specification <ftp://igs.org/pub/data/format/rinex303.pdf>`_, only certain fields are valid for particular satellite systems.
Not every receiver receives every type of GNSS system. 
Most Android devices in the Americas receive at least GPS and GLONASS.


Index OBS data
~~~~~~~~~~~~~~
assume the OBS data from a file is loaded in variable ``obs``.

---

Select satellite(s) (here, ``G13``) by

.. code:: python

    obs.sel(sv='G13').dropna(dim='time',how='all')


---


Pick any parameter (say, ``L1``) across all satellites and time (or index via ``.sel()`` by time and/or satellite too) by:


.. code:: python

    obs['L1'].dropna(dim='time',how='all')
    
    
---

Indexing only a particular satellite system (here, Galileo) using Boolean indexing.

.. code:: python

    import pyrinex as pr
    obs = pr.rinexobs('myfile.o', use='E')

would load only Galileo data by the parameter E.
ReadRinex.py allow this to be specified as the -use command line parameter.

If however you want to do this after loading all the data anyway, you can make a Boolean indexer

.. code:: python

    Eind = obs.sv.to_index().str.startswith('E')  # returns a simple Numpy boolean 1-D array

    Edata = obs.isel(sv=Eind)  # any combination of other indices at same time or before/after also possible

Plot OBS data
~~~~~~~~~~~~~
Plot for all satellites L1C:

.. code:: python

    from matplotlib.pyplot import figure, show

    ax = figure().gca()
    ax.plot(obs.time, obs['L1C'])

    show()



Suppose L1C psuedorange plot is desired for `G13`:

.. code:: python

    obs['L1C'].sel(sv='G13').dropna(dim='time',how='all').plot()


read Nav
--------
If you desire to specifically read a RINEX 2 or 3 NAV file:

.. code:: python

    nav = pr.rinexnav('tests/demo_MN.rnx')

This returns an ``xarray.Dataset`` of the data within the RINEX 3 or RINEX 2 Navigation file.
Indexed by time x quantity


Index NAV data
~~~~~~~~~~~~~~
assume the NAV data from a file is loaded in variable ``nav``.

Select satellite(s) (here, ``G13``) by

.. code:: python

    nav.sel(sv='G13')

Pick any parameter (say, ``M0``) across all satellites and time (or index by that first) by:


.. code:: python

    nav['M0']


Notes
=====

RINEX 3.03 `specification <ftp://igs.org/pub/data/format/rinex303.pdf>`_

* GPS satellite position is given for each time in the NAV file as Keplerian parameters, which can be `converted to ECEF <https://ascelibrary.org/doi/pdf/10.1061/9780784411506.ap03>`_.
* https://downloads.rene-schwarz.com/download/M001-Keplerian_Orbit_Elements_to_Cartesian_State_Vectors.pdf
* http://www.gage.es/gFD


RINEX OBS reader algorithm
--------------------------
1. read overall OBS header (so we know what to expect in the rest of the OBS file)
2. fill the xarray.Dataset with the data by reading in blocks -- another key difference from other programs out there, instead of reading character by character, I ingest a whole time step of text at once, helping keep the processing closer to CPU cache making it much faster.



Data
----

For `capable Android devices <https://developer.android.com/guide/topics/sensors/gnss.html>`_,
you can
`log RINEX 3 <https://play.google.com/store/apps/details?id=de.geopp.rinexlogger>`_
using the built-in GPS receiver.


Here is a lot of RINEX 3 data to work with:

* OBS `data <ftp://data-out.unavco.org/pub/rinex3/obs/>`_
* NAV `data <ftp://data-out.unavco.org/pub/rinex3/nav>`_

