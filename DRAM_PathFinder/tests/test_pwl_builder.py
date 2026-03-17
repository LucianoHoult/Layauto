"""Tests for PWL stimulus generation."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config_parser import ConfigParser
from core.pwl_builder import PWLBuilder


def test_pwl_generation_and_monotonic_time():
    config = ConfigParser(Path(__file__).resolve().parents[1] / "configs").load_all()
    stimulus = PWLBuilder().build(config)

    assert "VACT_CMD ACT_CMD 0 PWL(" in stimulus
    assert "VREAD_CMD READ_CMD 0 PWL(" in stimulus
    assert "2.000000e-11 1.200" in stimulus

    for line in stimulus.splitlines():
        if "PWL(" not in line:
            continue
        body = line.split("PWL(", 1)[1].rstrip(")")
        vals = [float(x) for x in re.findall(r"[-+]?\d+\.\d+e[+-]\d+", body)]
        times = vals[0::2]
        assert times == sorted(times)
