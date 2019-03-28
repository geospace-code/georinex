#!/usr/bin/env python
import pytest
from pytest import approx
from pathlib import Path
import georinex as gr
import xarray

R = Path(__file__).parent / 'data'

blanks = ['blank.10n', 'blank.10o', 'blank3.10n', 'blank3.10o']


@pytest.mark.parametrize('filename', blanks)
def test_blank_read(tmp_path, filename):
    dat = gr.load(R/filename)
    assert dat.time.size == 0


@pytest.mark.parametrize('filename', blanks)
def test_blank_write(tmp_path, filename):
    pytest.importorskip('netCDF4')
    gr.load(R/filename, tmp_path)


@pytest.mark.parametrize('filename', blanks)
def test_blank_times(filename):
    times = gr.gettime(R/filename)
    assert times.size == 0


@pytest.mark.parametrize('filename',
                         ['minimal2.10n', 'minimal3.10n', 'minimal2.10o', 'minimal3.10o'])
def test_minimal(tmp_path, filename):
    pytest.importorskip('netCDF4')

    fn = R/filename

    dat = gr.load(fn)
    assert isinstance(dat, xarray.Dataset), f'{type(dat)} should be xarray.Dataset'

    outdir = tmp_path
    gr.load(fn, outdir)

    outfn = (outdir / (fn.name + '.nc'))
    assert outfn.is_file()

    assert dat.equals(gr.load(outfn)), f'{outfn}  {fn}'

    times = gr.gettime(fn)
    assert times.size == 1

    if dat.rinextype == 'obs':
        if int(dat.version) == 2:
            assert dat.fast_processing
        elif int(dat.version) == 3:
            assert not dat.fast_processing  # FIXME: update when OBS3 fast processing is added.


@pytest.mark.parametrize('fn, version',
                         [('demo.10o', 2),
                          ('demo3.10o', 3),
                          ('demo.10n', 2),
                          ('demo3.10n', 3)],
                         ids=['OBS2', 'OBS3', 'NAV2', 'NAV3'])
def test_header(fn, version):
    hdr = gr.rinexheader(R/fn)

    assert isinstance(hdr, dict)
    assert int(hdr['version']) == version

    if 'fields' in hdr:
        assert len(hdr['position']) == 3


def test_dont_care_file_extension():
    """ GeoRinex ignores the file extension and only considers file headers to determine what a file is."""
    fn = R / 'brdc0320.16l.txt'

    hdr = gr.rinexheader(R/fn)
    assert int(hdr['version']) == 3

    nav = gr.load(fn)
    assert nav.ionospheric_corr_GAL == approx([139, 0.132, 0.0186])


if __name__ == '__main__':
    pytest.main([__file__])
