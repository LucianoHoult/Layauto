"""Prepare synthetic inputs for both wheel smoke runs."""
from pathlib import Path
from hashlib import sha256
import json
import sys

repo = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repo / 'tests/support'))
from analysis_inputs import load, manual_for, materialize, rebind, write

root = Path(sys.argv[1])
materialize(root / 'no_body')
materialize(root / 'body', body=True)
materialize(root / 'mismatch', case='extraction_mismatch')
materialize(root / 'bad_body', case='body_wrong_binding', body=True)
materialize(root / 'manual', manual=manual_for(root / 'no_body'))
both = root / 'combined'
materialize(both)
cdl = both / 'source.cdl'
cdl.write_text(cdl.read_text().replace('.SUBCKT INV_M1_SYNTH A Y VSS VDD', '.SUBCKT INV_M1_SYNTH A Y VSS'))
formats = both / 'tech/formats.json'
owner = load(formats)
owner['geometry_capability']['comparator'] = 'hypothetical_topology_comparator/9'
write(formats, owner)
rebind(both)
print(json.dumps({str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
                  for p in sorted(root.rglob('*')) if p.is_file()}, indent=2))
