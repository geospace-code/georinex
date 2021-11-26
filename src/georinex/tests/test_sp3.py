import pytest
from pytest import approx
from pathlib import Path
import georinex as gr

#
R = Path(__file__).parent / "data"


@pytest.mark.parametrize("fn", ["example1.sp3a", "example2.sp3a"])
def test_sp3a(fn):
    dat = gr.load(R / fn)

    d0 = dat.sel(time="1994-12-17T00:15:00")

    assert len(d0.sv) == 25

    G2 = d0.sel(sv="2")
    assert G2["position"].data == approx([-22813.261065, -9927.616864, -9816.490189])
    assert G2["clock"].item() == approx(-131.328686)


@pytest.mark.parametrize("fn", ["igs19362.sp3c"])
def test_sp3c(fn):
    dat = gr.load(R / fn)

    d0 = dat.sel(time="2017-02-14T00:15:00")

    assert len(d0.sv) == 32

    G20 = d0.sel(sv="G20")

    assert G20["position"].data == approx([-6468.900825, 14715.965428, 20990.8862])
    assert G20["clock"].item() == approx(459.946483)


def test_blank():
    with pytest.raises(ValueError):
        gr.load(R / "blank.sp3")


def test_header():
    with pytest.raises(ValueError):
        gr.load(R / "header.sp3")


def test_minimal_sp3c():
    dat = gr.load(R / "minimal.sp3c")

    d0 = dat.sel(time="2017-02-14T00:00:00")

    assert len(d0.sv) == 32

    G20 = d0.sel(sv="G20")

    assert G20["position"].values == approx([-4091.382501, 15329.987734, 21147.362623])
    assert G20.clock.item() == approx(459.944522)


def test_minimal_sp3d():
    dat = gr.load(R / "minimal.sp3d")
    d0 = dat.sel(time="2020-01-24T00:00:00")
    assert len(d0.sv) == 116
    E21 = d0.sel(sv="E21")
    assert E21["position"].values == approx([26228.497812, 1498.630544, -13647.911806])
    assert E21.clock.item() == approx(-578.689388)


# perhaps not a valid test?
# def test_truncated():
#     dat = gr.load(R / "truncated.sp3")

#     d0 = dat.sel(time="2017-02-14T00:35:00")

#     G20 = d0.sel(sv="G20")

#     assert np.isnan(G20.clock.item())
