#!/usr/bin/env python
"""
test console script
"""
import pytest
import subprocess
from pathlib import Path

R = Path(__file__).parent


def test_convenience():
    subprocess.check_call(['ReadRinex', '-q', str(R / 'demo.10o')])


def test_time():
    subprocess.check_call(['TimeRinex', '-q', str(R)])


if __name__ == '__main__':
    pytest.main(['-x', __file__])
