#!/usr/bin/env python
import subprocess
import pytest
from pathlib import Path
import georinex as gr
from datetime import datetime
import os

R = Path(__file__).parent
Rexe = Path(__file__).resolve().parents[1] / 'rnxcmp'
exe = './crx2rnx'
shell = False
if os.name == 'nt':
    exe = exe[2:]
    shell = True

try:  # capture_output is py >= 3.7
    ret = subprocess.run([exe, '-h'], stderr=subprocess.PIPE,
                         universal_newlines=True, cwd=Rexe, shell=shell)  # -h returncode == 1
    nocrx = False if ret.stderr.startswith('Usage') else True
except (FileNotFoundError, PermissionError) as e:
    print(e)
    nocrx = True


@pytest.mark.skipif(nocrx, reason=f'crx2rnx not found in {Rexe}')
@pytest.mark.timeout(30)
def test_obs3():
    fn = R / 'CEBR00ESP_R_20182000000_01D_30S_MO.crx.gz'

    info = gr.rinexinfo(fn)

    assert info['hatanaka']
    assert int(info['version']) == 3
# %% full file
    obs = gr.load(fn, tlim=('2018-07-19T01', '2018-07-19T01:10'))

    assert (obs.sv.values == ['C05', 'C10', 'C14', 'C22', 'C31', 'E01', 'E04', 'E09', 'E11',
                              'E19', 'E21', 'E31', 'G02', 'G05', 'G07', 'G13', 'G15', 'G21',
                              'G24', 'G28', 'G30', 'R03', 'R04', 'R05', 'R13', 'R14', 'R15',
                              'R16', 'R21', 'S20', 'S23', 'S25', 'S47', 'S48']).all()

    times = obs.time.values.astype('datetime64[us]').astype(datetime)

    assert times[0] == datetime(2018, 7, 19, 1)
    assert times[-1] == datetime(2018, 7, 19, 1, 10)


if __name__ == '__main__':
    pytest.main(['-x', __file__])
