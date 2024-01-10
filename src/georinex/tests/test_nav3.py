from pathlib import Path
import pytest
from pytest import approx
import xarray
from datetime import datetime
import georinex as gr


R = Path(__file__).parent / "data"


@pytest.mark.parametrize("fname", ["demo_nav3.17n"])
def test_nav3header(fname):
    hdr = gr.rinexheader(R / fname)
    assert hdr["IONOSPHERIC CORR"]["GPSA"] == approx(
        [1.1176e-08, -1.4901e-08, -5.9605e-08, 1.1921e-07]
    )
    assert hdr["TIME SYSTEM CORR"]["GPUT"] == approx(
        [-3.7252902985e-09, -1.065814104e-14, 61440, 1976]
    )


@pytest.mark.parametrize("fname", ["VILL00ESP_R_20181700000_01D_MN.rnx.gz"])
def test_time(fname):
    times = gr.gettime(R / fname)

    assert times[0] == datetime(2018, 4, 24, 8)
    assert times[-1] == datetime(2018, 6, 20, 22)


@pytest.mark.parametrize("fname", ["CEDA00USA_R_20182100000_01D_MN.rnx.gz"])
def test_tlim_past_eof(fname):
    fn = R / fname
    nav = gr.load(fn, tlim=("2018-07-29T23", "2018-07-29T23:30"))

    times = gr.to_datetime(nav.time)

    assert times == datetime(2018, 7, 29, 23)


@pytest.mark.parametrize("fname", ["spare_filled_nav3.rnx"])
def test_spare(fname):
    """
    NAV3 with filled spare fields (many files omit the spare fields)
    """

    fn = R / fname
    nav = gr.load(fn)
    G01 = nav.sel(sv="G01").dropna(dim="time", how="all")
    assert G01.time.size == 2
    assert (G01["FitIntvl"] == approx([4.0, 4.0])).all()


@pytest.mark.parametrize("fname", ["ELKO00USA_R_20182100000_01D_MN.rnx.gz"])
def test_mixed(fname):
    fn = R / fname
    nav = gr.load(fn, tlim=(datetime(2018, 7, 28, 21), datetime(2018, 7, 28, 23)))

    E04 = nav.sel(sv="E04").dropna(dim="time", how="all")
    E04_1 = nav.sel(sv="E04_1").dropna(dim="time", how="all")

    E04tt = E04["TransTime"].values
    E04_1tt = E04_1["TransTime"].values

    assert E04tt != approx(E04_1tt)

    assert isinstance(nav, xarray.Dataset)
    assert set(nav.svtype) == {"C", "E", "G", "R"}

    times = gr.to_datetime(nav.time)

    assert times.size == 15
    # %% full flle test
    nav = gr.load(fn)

    svin = {
        "C06",
        "C07",
        "C08",
        "C11",
        "C12",
        "C14",
        "C16",
        "C20",
        "C21",
        "C22",
        "C27",
        "C29",
        "C30",
        "E01",
        "E02",
        "E03",
        "E04",
        "E05",
        "E07",
        "E08",
        "E09",
        "E11",
        "E12",
        "E14",
        "E18",
        "E19",
        "E21",
        "E24",
        "E25",
        "E26",
        "E27",
        "E30",
        "E31",
        "G01",
        "G02",
        "G03",
        "G04",
        "G05",
        "G06",
        "G07",
        "G08",
        "G09",
        "G10",
        "G11",
        "G12",
        "G13",
        "G14",
        "G15",
        "G16",
        "G17",
        "G18",
        "G19",
        "G20",
        "G21",
        "G22",
        "G23",
        "G24",
        "G25",
        "G26",
        "G27",
        "G28",
        "G29",
        "G30",
        "G31",
        "G32",
        "R01",
        "R02",
        "R03",
        "R04",
        "R05",
        "R06",
        "R07",
        "R08",
        "R09",
        "R10",
        "R11",
        "R12",
        "R13",
        "R14",
        "R15",
        "R16",
        "R17",
        "R18",
        "R19",
        "R20",
        "R21",
        "R22",
        "R23",
        "R24",
    }
    assert len(svin.intersection(nav.sv.values)) == len(svin)

    C05 = nav.sel(sv="C06").dropna(how="all", dim="time")
    E05 = nav.sel(sv="E05").dropna(how="all", dim="time")

    assert C05.time.size == 3  # from inspection of file
    assert E05.time.size == 22  # duplications in file at same time--> take first time


@pytest.mark.parametrize(
    "filename, sv, shape",
    [
        ("VILL00ESP_R_20181700000_01D_MN.rnx.gz", "S36", (542, 15)),
        ("VILL00ESP_R_20181700000_01D_MN.rnx.gz", "G05", (7, 31)),
        ("VILL00ESP_R_20181700000_01D_MN.rnx.gz", "C05", (25, 31)),
        ("VILL00ESP_R_20181700000_01D_MN.rnx.gz", "E05", (45, 31)),
        ("VILL00ESP_R_20181700000_01D_MN.rnx.gz", "R05", (19, 15)),
    ],
    ids=["SBAS", "GPS", "BDS", "GAL", "GLO"],
)
def test_large(filename, sv, shape):
    nav = gr.load(R / filename, use=sv[0])

    assert nav.svtype[0] == sv[0] and len(nav.svtype) == 1

    dat = nav.sel(sv=sv).dropna(how="all", dim="time")

    assert dat.time.size == shape[0]
    assert len(dat.data_vars) == shape[1]

    for v in dat.data_vars:
        if v.startswith("spare"):
            continue
        assert all(dat[v].notnull())


@pytest.mark.parametrize(
    "sv, size", [("C05", 25), ("E05", 45), ("G05", 7), ("R05", 19), ("S36", 542)]
)
def test_large_all(sv, size):
    fn = R / "VILL00ESP_R_20181700000_01D_MN.rnx.gz"
    nav = gr.load(fn)
    assert set(nav.svtype) == {"C", "E", "G", "R", "S"}

    dat = nav.sel(sv=sv).dropna(how="all", dim="time")
    assert dat.time.size == size  # manually counted from file


@pytest.mark.parametrize(
    "rfn, ncfn",
    [
        ("galileo3.15n", "galileo3.15n.nc"),
        ("demo_nav3.17n", "demo_nav3.17n.nc"),
        ("qzss_nav3.14n", "qzss_nav3.14n.nc"),
        ("demo_nav3.10n", "demo_nav3.10n.nc"),
    ],
    ids=["GAL", "GPS", "QZSS", "SBAS"],
)
def test_ref(rfn, ncfn):
    """
    python -m georinex.read src/georinex/tests/data/galileo3.15n -o galileo3.15n.nc
    python -m georinex.read src/georinex/tests/data/demo_nav3.17n -o demo_nav3.17n.nc
    python -m georinex.read src/georinex/tests/data/qzss_nav3.14n -o qzss_nav3.14n.nc
    python -m georinex.read src/georinex/tests/data/demo_nav3.10n -o demo_nav3.10n.nc
    """
    pytest.importorskip("netCDF4")

    truth = gr.load(R / ncfn)
    nav = gr.load(R / rfn)

    for v in nav.data_vars:
        assert truth[v].equals(nav[v])
    assert nav.equals(truth)


def test_ionospheric_correction():
    nav = gr.load(R / "demo_nav3.17n")

    assert nav.attrs["ionospheric_corr_GPS"] == approx(
        [
            1.1176e-08,
            -1.4901e-08,
            -5.9605e-08,
            1.1921e-07,
            9.8304e04,
            -1.1469e05,
            -1.9661e05,
            7.2090e05,
        ]
    )

    nav = gr.load(R / "galileo3.15n")

    assert nav.attrs["ionospheric_corr_GAL"] == approx([0.1248e03, 0.5039, 0.2377e-01])

def test_missing_fields():
    """Tests the conditions when missing fields exist within rinex data.

    """
    nav = gr.load(R / "BRDC00IGS_R_20201360000_01D_MN.rnx", use='E', verbose=True)
    # missing fields should be interpretted as zero and not NaN
    # no NaN values should exist when loading the provided rinex file
    assert nav.to_dataframe().isna().sum().sum() == 0

def test_missing_fields_end_of_line():
    """Test when missing fields are at the end of the line.

    In the test file, the J01 is missing the "FitIntvl" field which is
    the final field. According to the Rinex specification, that missing
    value should be interpretted as 0.

    """
    nav = gr.load(R / "BRDM00DLR_R_20130010000_01D_MN.rnx", use='J', verbose=True)
    assert nav.to_dataframe()["FitIntvl"].to_list() == [0.,0.]
