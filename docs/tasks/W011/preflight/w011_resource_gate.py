"""Execution-only W011 memory gate; never changes test items, fixtures or outcomes.

The setup wrapper takes the shared Linux flock before fixture setup for the first
``test_w011_*`` item. The raw descriptor is intentionally retained until process
exit: the OS releases it only when this pytest process and its retained memory
exit. Session finish logs that retention; the parent runner separately records
when subprocess completion was observed. A killed process may have no finish log.
"""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path

import pytest

_LOCK_FD: int | None = None
_LOCK_PATH: str | None = None
_LOG_PATH: str | None = None
_FIRST_NODE: str | None = None
_PLUGIN_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _event(event: str, lock_fd: int) -> None:
    assert _LOG_PATH is not None
    identity = os.fstat(lock_fd)
    row = {'event': event, 'observed_at_utc': datetime.now(timezone.utc).isoformat(),
           'pid': os.getpid(), 'first_gated_node': _FIRST_NODE,
           'lock_path': _LOCK_PATH, 'lock_device': identity.st_dev,
           'lock_inode': identity.st_ino, 'lock_fd_inheritable': os.get_inheritable(lock_fd),
           'plugin_sha256': _PLUGIN_SHA}
    descriptor = os.open(_LOG_PATH, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        data = (json.dumps(row, sort_keys=True) + '\n').encode()
        assert os.write(descriptor, data) == len(data)
    finally:
        os.close(descriptor)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption('--w011-resource-lock', required=True)
    parser.addoption('--w011-resource-log', required=True)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_setup(item: pytest.Item):
    global _LOCK_FD, _LOCK_PATH, _LOG_PATH, _FIRST_NODE
    if _LOCK_FD is None and Path(str(item.path)).name.startswith('test_w011_'):
        _LOCK_PATH = str(Path(item.config.getoption('--w011-resource-lock')).absolute())
        _LOG_PATH = str(Path(item.config.getoption('--w011-resource-log')).absolute())
        _FIRST_NODE = item.nodeid
        descriptor = os.open(_LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            _event('WAIT', descriptor)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        except BaseException:
            os.close(descriptor)
            raise
        _LOCK_FD = descriptor
        _event('ACQUIRED', descriptor)
    yield


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int):
    try:
        yield
    finally:
        if _LOCK_FD is not None:
            _event('SESSION_FINISH_LOCK_RETAINED', _LOCK_FD)
    # Do not unlock or close _LOCK_FD here. Keep the guard until process exit.
