#!/usr/bin/env python
import pytest
from pathlib import Path

import georinex as gr

try:
    import netCDF4
except ImportError:
    netCDF4 = None

R = Path(__file__).parent / 'data'


@pytest.mark.parametrize('fn, rtype, vers', [(R/'minimal2.10o', 'obs', 2.11),
                                             (R/'minimal3.10o', 'obs', 3.01),
                                             (R/'minimal2.10n', 'nav', 2.11),
                                             (R/'minimal3.10n', 'nav', 3.01),
                                             (R/'york0440.15d', 'obs', 1.00),
                                             (R/'r2all.nc', 'obs', 2.11)],
                         ids=['obs2', 'obs3', 'nav2', 'nav3', 'Cobs1', 'NetCDF_obs2'])
def test_header(fn, rtype, vers):

    if fn.suffix == '.nc' and netCDF4 is None:
        pytest.skip('no netCDF4')

    hdr = gr.rinexheader(fn)
    assert isinstance(hdr, dict)
    assert rtype in hdr['rinextype']
    assert hdr['version'] == pytest.approx(vers)

    # make sure string filenames work too
    hdr = gr.rinexheader(str(fn))
    assert isinstance(hdr, dict)


@pytest.mark.parametrize('fn',
                         [R/'demo.10o', R/'demo3.10o'],
                         ids=['obs2', 'obs3'])
def test_position(fn):
    hdr = gr.rinexheader(fn)
    assert len(hdr['position']) == 3


if __name__ == '__main__':
    pytest.main([__file__])
