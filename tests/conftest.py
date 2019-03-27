import pytest
import os
import subprocess
from pathlib import Path


@pytest.fixture(autouse=True)
def init_cache(request):
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

    C = {'shell': shell, 'nocrx': nocrx, 'Rexe': str(Rexe)}

    request.config.cache.set('exe', C)
