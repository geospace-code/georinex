#!/usr/bin/env python
"""
test console script
"""
import pytest
import subprocess
import sys
from pathlib import Path

R = Path(__file__).parent / "data"
Rexe = Path(__file__).resolve().parents[1]


def test_convenience():
    subprocess.check_call([sys.executable, "ReadRinex.py", str(R / "demo.10o")], cwd=Rexe)


def test_time():
    subprocess.check_call([sys.executable, "TimeRinex.py", str(R)], cwd=Rexe)


# %% convert all OBS 2 files to NetCDF4
pat = "*.*o"
flist = list(R.glob(pat))
assert len(flist) > 0


@pytest.mark.parametrize("filename", flist, ids=[f.name for f in flist])
def test_batch_convert(tmp_path, filename):
    pytest.importorskip("netCDF4")

    if filename.name.startswith("blank"):
        return  # this file has no contents, hence nothing to convert to NetCDF4

    outdir = tmp_path
    subprocess.check_call([sys.executable, "rnx2hdf5.py", str(R), "*o", "-o", str(outdir)], cwd=Rexe)

    outfn = outdir / (filename.name + ".nc")
    assert outfn.is_file()
    assert outfn.stat().st_size > 30000, f"{outfn}"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
