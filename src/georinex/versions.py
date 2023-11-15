import xarray
import numpy
import sys
import pandas
import netCDF4

from . import __version__

print("Georinex", __version__)
print("Python", sys.version, sys.platform)
print("xarray", xarray.__version__)
print("Numpy", numpy.__version__)
print("Pandas", pandas.__version__)
print("NetCDF4", netCDF4.__version__)

try:
    import pytest

    print("Pytest", pytest.__version__)
except ImportError:
    pass
