from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path('/workspace/Layauto')
base = root / 'docs/tasks/W012/A2-implementation'
record = base / 'development/affected-r1.command.json'
last = None
while True:
    try:
        status = json.loads(record.read_text())
    except json.JSONDecodeError:
        time.sleep(1)
        continue
    if 'exit_code' in status:
        break
    now = int(time.monotonic() // 60)
    if now != last:
        output = (base / 'development/affected-r1.stdout.txt').read_text()
        print(datetime.now(timezone.utc).isoformat(), 'WAIT affected regression; progress characters', len(output), flush=True)
        last = now
    time.sleep(10)
assert status['exit_code'] == 0, 'affected regression failed; screen not started'
heavy = []
for p in Path('/proc').iterdir():
    if not p.name.isdigit() or int(p.name) == os.getpid():
        continue
    try:
        cmd = (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
        fields = dict(line.split(':', 1) for line in (p / 'status').read_text().splitlines() if ':' in line)
        rss = int(fields.get('VmRSS', '0 kB').split()[0])
        if ('python' in cmd or 'pytest' in cmd) and rss > 100000:
            heavy.append({'pid': int(p.name), 'rss_kib': rss, 'command': cmd})
    except (FileNotFoundError, ProcessLookupError):
        pass
assert not heavy, ('other heavy process present; screen not started', heavy)
print(datetime.now(timezone.utc).isoformat(), 'Affected regression exit0, no other heavy Python; starting r1', flush=True)
runner = [sys.executable, '-B', str(base / 'run_command.py'), '--cwd', str(root), '--out', str(base / 'development/performance-r1'), '--', sys.executable, '-B', str(base / 'measurement/run.py'), '--freeze', str(base / 'freeze-screen/freeze.json'), '--out', str(base / 'performance'), '--wires', '/workspace/work/w012-a2/wires', '--reps', '1']
result = subprocess.run(runner, cwd=root, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
assert result.returncode == 0, 'screen failed; all original outputs preserved'
analyzer = [sys.executable, '-B', str(base / 'run_command.py'), '--cwd', str(root), '--out', str(base / 'development/screen-analysis-r1'), '--', sys.executable, '-B', str(base / 'measurement/analyze.py'), '--samples', str(base / 'performance'), '--reps', '1', '--output', str(base / 'screening-summary.json')]
result = subprocess.run(analyzer, cwd=root, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
assert result.returncode == 0, 'analysis failed; original outputs preserved'
print('SCREEN and analysis finished successfully', flush=True)
