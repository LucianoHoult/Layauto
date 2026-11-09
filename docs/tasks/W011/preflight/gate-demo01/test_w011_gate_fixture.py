"""Engineering guard probe only, outside official source/test snapshot."""
import fcntl
import os
from pathlib import Path
import time
import pytest


def must_already_hold_gate(request, phase):
    descriptor = os.open(request.config.getoption('--w011-resource-lock'), os.O_RDWR)
    try:
        with pytest.raises(BlockingIOError):
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(descriptor)
    with Path(request.config.getoption('--w011-resource-log') + '.fixture.txt').open('a') as log:
        log.write(phase + '\n')


@pytest.fixture(scope='session', autouse=True)
def session_witness(request):
    must_already_hold_gate(request, 'session_fixture_setup_guarded')
    yield
    must_already_hold_gate(request, 'session_fixture_teardown_guarded')


@pytest.fixture(scope='module', autouse=True)
def module_witness(request):
    must_already_hold_gate(request, 'module_fixture_setup_guarded')
    yield
    must_already_hold_gate(request, 'module_fixture_teardown_guarded')


def test_gate_is_held_before_fixtures_and_during_body(request):
    must_already_hold_gate(request, 'test_body_guarded')
    time.sleep(0.5)
