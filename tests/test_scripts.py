#!/usr/bin/env python
"""
test console script
"""
import pytest
import subprocess
from pathlib import Path

rdir = Path(__file__).parent


def test_convenience():

    subprocess.check_call(['ReadRinex', '-q', str(rdir / 'demo.10o')])


if __name__ == '__main__':
    pytest.main()
