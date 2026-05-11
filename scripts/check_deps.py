"""Dependency check + one-click install for Buffer Fin Resize MVP.

Behaviour:
  * ``python scripts/check_deps.py``           — report status only.
  * ``python scripts/check_deps.py --install`` — pip-install anything missing.
  * ``python scripts/check_deps.py --upgrade`` — pip-install --upgrade everything.

Runs on Windows / Linux / macOS with stdlib only (no external deps
required for the check itself). All file I/O is explicit UTF-8 so it
behaves identically on Windows zh-CN locales that default to GBK.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata as md
import platform
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple

# (import_name, pip_name, min_version_or_None, required)
# import_name differs from pip name for pyyaml (import yaml) and pillow etc.
DEPS: List[Tuple[str, str, Optional[str], bool]] = [
    ('numpy',       'numpy',       '1.23', True),
    ('matplotlib',  'matplotlib',  '3.6',  True),
    ('yaml',        'pyyaml',      '6.0',  True),
    ('gdstk',       'gdstk',       '0.9',  False),
    ('pytest',      'pytest',      '7.0',  False),
    ('klayout',     'klayout',     None,   False),
]

MIN_PYTHON = (3, 10)


def _ver_tuple(v: str) -> Tuple[int, ...]:
    out = []
    for part in v.split('.'):
        try:
            out.append(int(''.join(c for c in part if c.isdigit())))
        except ValueError:
            out.append(0)
    return tuple(out)


def _check_python() -> bool:
    cur = sys.version_info[:2]
    ok = cur >= MIN_PYTHON
    flag = 'OK' if ok else 'FAIL'
    print(f"[{flag}] Python {cur[0]}.{cur[1]} "
          f"(need >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})")
    return ok


def _installed_version(import_name: str, pip_name: str) -> Optional[str]:
    try:
        importlib.import_module(import_name)
    except Exception:
        return None
    for name in (pip_name, import_name):
        try:
            return md.version(name)
        except md.PackageNotFoundError:
            continue
    return ''


def _check_one(import_name: str, pip_name: str,
               min_ver: Optional[str], required: bool) -> Tuple[bool, Optional[str]]:
    """Return (satisfied, installed_version or None)."""
    ver = _installed_version(import_name, pip_name)
    if ver is None:
        return (not required, None)
    if min_ver and ver and _ver_tuple(ver) < _ver_tuple(min_ver):
        return (False, ver)
    return (True, ver)


def _print_report() -> Tuple[List[str], List[str]]:
    """Print a status table. Returns (missing_required, missing_optional)
    pip-install names (those failing the version floor count as 'missing')."""
    missing_req: List[str] = []
    missing_opt: List[str] = []
    print(f"\nPlatform: {platform.system()} {platform.release()} "
          f"({platform.machine()})")
    print(f"Python  : {sys.executable}")
    print()
    print(f"  {'Package':<14} {'Required':<9} {'Min':<8} {'Installed':<12} Status")
    print(f"  {'-'*14} {'-'*9} {'-'*8} {'-'*12} {'-'*8}")
    for import_name, pip_name, min_ver, required in DEPS:
        ok, ver = _check_one(import_name, pip_name, min_ver, required)
        req_str = 'yes' if required else 'optional'
        ver_str = ver if ver else '-'
        if ok and ver:
            status = 'OK'
        elif ok and not ver:
            status = 'skip'  # optional, not installed, no action
        else:
            status = 'MISSING' if not ver else 'OLD'
            (missing_req if required else missing_opt).append(pip_name)
        print(f"  {pip_name:<14} {req_str:<9} {(min_ver or '-'):<8} "
              f"{ver_str:<12} {status}")
    return missing_req, missing_opt


def _pip_install(packages: List[str], upgrade: bool = False) -> int:
    if not packages:
        return 0
    cmd = [sys.executable, '-m', 'pip', 'install']
    if upgrade:
        cmd.append('--upgrade')
    cmd.extend(packages)
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true',
                        help='pip-install any missing required dependencies.')
    parser.add_argument('--with-optional', action='store_true',
                        help='Also install optional deps '
                             '(gdstk, pytest). Implies --install.')
    parser.add_argument('--upgrade', action='store_true',
                        help='Run pip install --upgrade on all listed deps.')
    args = parser.parse_args()

    if not _check_python():
        print("\nPython version below minimum. "
              "Install Python 3.10+ before continuing.")
        return 1

    missing_req, missing_opt = _print_report()

    if args.upgrade:
        all_pkgs = [p for _, p, _, _ in DEPS if p != 'klayout']
        rc = _pip_install(all_pkgs, upgrade=True)
        if rc:
            return rc
        print("\nAll listed dependencies upgraded.")
        return 0

    if args.install or args.with_optional:
        to_install = list(missing_req)
        if args.with_optional:
            to_install.extend(missing_opt)
        if not to_install:
            print("\nNothing to install — required deps already satisfied.")
            return 0
        rc = _pip_install(to_install)
        if rc:
            print("\npip install failed. See output above.")
            return rc
        # Re-check to confirm.
        print("\nRe-checking after install...")
        missing_req, _ = _print_report()
        if missing_req:
            print("\nSome required deps still missing after install:", missing_req)
            return 1
        print("\nAll required dependencies satisfied.")
        return 0

    # Report-only mode.
    if missing_req:
        print(f"\n{len(missing_req)} required dependency(ies) missing: "
              f"{', '.join(missing_req)}")
        print("Run with --install (or --with-optional) to fix.")
        return 1
    if missing_opt:
        print(f"\n{len(missing_opt)} optional dep(s) not installed: "
              f"{', '.join(missing_opt)} — pass --with-optional to install.")
    print("\nRequired dependencies satisfied.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
