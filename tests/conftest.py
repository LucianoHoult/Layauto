"""Shared pytest fixtures for all tests."""

import os
import json
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '..', 'dummy', 'fixtures')


@pytest.fixture
def fixture_dir():
    return FIXTURE_DIR


@pytest.fixture
def original_layout_json():
    path = os.path.join(FIXTURE_DIR, 'buffer_original.json')
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def target_layout_json():
    path = os.path.join(FIXTURE_DIR, 'buffer_target.json')
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def calibre_device_json():
    path = os.path.join(FIXTURE_DIR, 'calibre_device_query.json')
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def calibre_net_json():
    path = os.path.join(FIXTURE_DIR, 'calibre_net_query.json')
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def ixref_temp_path():
    return os.path.join(FIXTURE_DIR, 'iXref.temp')


@pytest.fixture
def nxref_temp_path():
    return os.path.join(FIXTURE_DIR, 'nXref.temp')


@pytest.fixture
def net_names_path():
    return os.path.join(FIXTURE_DIR, 'net_names.txt')
