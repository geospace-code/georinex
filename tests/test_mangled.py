#!/usr/bin/env python
"""
many different ways RINEX files could be invalid.
Please let us know if you have more examples.
"""
import pytest
import georinex as gr
import numpy as np
import io

UTF8 = '✓'
long = 'ဇၟာပ်မၞိဟ်ဂှ် ကတဵုဒှ်ကၠုင်လဝ် နကဵု ဂုဏ်သိက္ခာကီု နကဵု အခေါင်အရာကီု တုပ်သၟဟ် ရေင်သကအ် သီုညးဖအိုတ်ရ၊၊ ကောန်မၞိဟ်တအ်ဂှ် ဟိုတ်မၞုံကဵုအစောံသတ္တိ မပါ်ပါဲ ဟိုတ်ဖိုလ် ကေုာံ ခိုဟ်ပရေအ်တအ်တုဲ ညးမွဲကေုာံညးမွဲ သ္ဒးဆက်ဆောံ နကဵု စိုတ်ကောဒေအ်ရ၊၊'
first = {'nav2': '     2.11           N: GPS NAV. MESSAGE                     RINEX VERSION / TYPE',
         'obs2': '     2.11           OBSERVATION DATA    M (MIXED)           RINEX VERSION / TYPE',
         'nav3': '     3.01           N: GNSS NAV DATA    S: SBAS             RINEX VERSION / TYPE',
         'obs3': '     3.01           OBSERVATION DATA    M (MIXED)           RINEX VERSION / TYPE'}

@pytest.mark.parametrize('hdr', first.values(), ids=list(first.keys()))
def test_first_line_ok(hdr):

    hio = io.StringIO(hdr)

    assert isinstance(gr.rinexheader(hio), dict)

    assert len(gr.gettime(hio)) == 0

    ds = gr.load(hio)

    if 'sv' in ds.coords:
        assert len(ds.sv) == 0

    if 'time' in ds.coords:
        assert len(ds.time) == 0



@pytest.mark.parametrize('hdr', first.values(), ids=list(first.keys()))
def test_first_line_ok_blank_lines(hdr):

    hio = io.StringIO(hdr+' '*80 + '\n')

    assert isinstance(gr.rinexheader(hio), dict)

    assert len(gr.gettime(hio)) == 0

    ds = gr.load(hio)

    if 'sv' in ds.coords:
        assert len(ds.sv) == 0

    if 'time' in ds.coords:
        assert len(ds.time) == 0


@pytest.mark.parametrize('val',
                         (None, '', b'', [], (), {}, {''}, np.empty(0), io.StringIO(''), io.BytesIO(b'')))
def test_null(val, tmp_path):
    with pytest.raises((ValueError, IsADirectoryError)):
        gr.load(val)

    with pytest.raises((ValueError, IsADirectoryError)):
        gr.rinexnav(val)

    with pytest.raises((ValueError, IsADirectoryError)):
        gr.rinexobs(val)

    with pytest.raises((ValueError, IsADirectoryError)):
        gr.rinexinfo(val)

    with pytest.raises((ValueError, IsADirectoryError)):
        gr.rinextype(val)

    with pytest.raises((ValueError, IsADirectoryError)):
        gr.rinexheader(val)

    with pytest.raises((ValueError, IsADirectoryError)):
        gr.navheader2(val)

    with pytest.raises((ValueError, IsADirectoryError)):
        gr.navheader3(val)

    with pytest.raises((ValueError, IsADirectoryError)):
        gr.obsheader2(val)

    with pytest.raises((ValueError, IsADirectoryError)):
        gr.obsheader3(val)

    with pytest.raises((TypeError, ValueError, IndexError, KeyError, IsADirectoryError)):
        gr.getlocations(val)

    with pytest.raises((ValueError, IsADirectoryError)):
        gr.gettime(val)

    if val != '':
        with pytest.raises((TypeError)):
            gr.batch_convert(val, '*', tmp_path)


@pytest.mark.parametrize('val',
                         [0,
                          io.StringIO(UTF8),
                          io.StringIO(long),
                          io.BytesIO(long.encode('utf8'))])
def test_non_rinex(val, tmp_path):
    with pytest.raises(ValueError):
        gr.load(val)

    with pytest.raises(ValueError):
        gr.rinexnav(val)

    with pytest.raises(ValueError):
        gr.rinexobs(val)

    with pytest.raises((ValueError)):
        gr.rinexinfo(val)

    with pytest.raises((ValueError)):
        gr.rinextype(val)

    with pytest.raises((ValueError)):
        gr.rinexheader(val)

    with pytest.raises((ValueError)):
        gr.rinextype(val)

    with pytest.raises((ValueError)):
        gr.navheader2(val)

    with pytest.raises((ValueError)):
        gr.navheader3(val)

    with pytest.raises((ValueError)):
        gr.obsheader2(val)

    with pytest.raises((ValueError)):
        gr.obsheader3(val)

    with pytest.raises((TypeError, ValueError)):
        gr.getlocations(val)

    with pytest.raises(ValueError):
        gr.gettime(val)

    with pytest.raises((TypeError)):
        gr.batch_convert(val, '*', tmp_path)


if __name__ == '__main__':
    pytest.main(['-x', __file__])