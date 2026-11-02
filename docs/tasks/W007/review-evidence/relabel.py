from pathlib import Path
import sys
REPOSITORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY))
sys.path.insert(0, str(REPOSITORY / "tests/contracts"))

import tempfile
from pathlib import Path
from dataclasses import replace
from w005_cases import copy_input, apply_case, without_cache, rebind
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result,normalize
from layauto_v2.domain.normalization import DeviceIdentity,NetIdentity,DeviceAnnotationSeed,NetAnnotationSeed,NormalizationResult
from layauto_v2.domain.identifiers import QueryKey

def make_full(parsed):
    outcome=normalize(from_parse_result(parsed))
    facts=outcome.completed
    cell=next(c for c in facts.source.cells if c.id==facts.source.selected_cell)
    devices={d.id.name:d.id for d in cell.devices}
    nets={n.id.name:n.id for n in cell.nets}
    header=parsed.value['header'];query=parsed.value['query']
    def key(kind, row):
        return QueryKey(header['header_id'],header['query_run_id'],header['query_database_id'],kind,row['layout_instance'] if kind=='device' else row['lvs_name'],None if kind=='device' else row['lvs_index'])
    d=[];used=set()
    for row in query['instance_xref']['records']:
        if row['schematic_instance'] in used: continue
        used.add(row['schematic_instance'])
        d.append(DeviceIdentity(devices[row['schematic_instance']],key('device',row),row['sd_swap'],row))
    n=[NetIdentity(nets[row['schematic_name']],key('net',row),row) for row in query['net_xref']['records']]
    ds=[DeviceAnnotationSeed(devices[row['schematic_instance']],key('device',row),row) for row in query['device_regions']['records']]
    ns=[NetAnnotationSeed(nets[row['schematic_name']],key('net',row),row) for row in query['net_regions']['records']]
    full=replace(facts,device_identities=d,net_identities=n,device_seeds=ds,net_seeds=ns)
    success=NormalizationResult('success',full,(),full,outcome.input)
    print('real',outcome.status,outcome.issues[0].code,'relabel:',success.status,'xref_rows:',len(query['instance_xref']['records']),'identity_count:',len(d),'swap_flags:',[x.sd_swap for x in d])

for case in ('device_reduction','swap'):
    with tempfile.TemporaryDirectory(prefix='w007-review-') as d:
        root=copy_input(Path(d))
        if case=='swap':
            path=root/'query/raw/iXref.temp'
            path.write_text(path.read_text().replace('0 Q17 0 MN0','0 Q17 0 MN0 X'))
        else: apply_case(root,case)
        without_cache(root);rebind(root)
        parsed=read_inputs(root/'site_config.yaml')
        assert parsed.status=='success',parsed.issues
        make_full(parsed)
