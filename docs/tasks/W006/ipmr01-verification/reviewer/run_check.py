"""Record one reviewer command without changing the tested checkout."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

output = Path(sys.argv[1])
command = sys.argv[2:]
started = time.monotonic()
result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
output.write_bytes(result.stdout)
metadata = {
    'command': command, 'cwd': str(Path.cwd()),
    'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'returncode': result.returncode, 'elapsed_seconds': round(time.monotonic() - started, 3),
    'output_sha256': hashlib.sha256(result.stdout).hexdigest(),
}
output.with_suffix('.result.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
print(result.stdout.decode(errors='replace')[-2000:])
sys.exit(result.returncode)
