from pathlib import Path
import sys
REPOSITORY = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPOSITORY))
sys.path.insert(0, str(REPOSITORY / "tests/contracts"))

import json
import tempfile
from pathlib import Path
from dataclasses import replace
from w005_cases import copy_input,write_json
from w006_cases import caller_request
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.domain.publication import InputsReady
from layauto_v2.normalization import from_inputs_ready, normalize
from layauto_v2.normalization.codec import encode_record,decode_record
with tempfile.TemporaryDirectory(prefix='w007-alias-') as d:
    root=copy_input(Path(d))
    (root/'source-alias.cdl').symlink_to('source.cdl')
    header=json.loads((root/'query/header.json').read_text())
    header['source_netlist']['uri']='source-alias.cdl'
    write_json(root/'query/header.json',header)
    repo=PublicationRepository()
    ready=prepare_inputs(repo,caller_request(root))
    assert isinstance(ready,InputsReady)
    inp=from_inputs_ready(ready,repo.read(ready.checkpoint_ref),repo.read(ready.parse_ref),repo.read(ready.tool_ref),tuple(repo.read(ref) for ref in ready.evidence_refs))
    res=normalize(inp)
    print('W006 alias readback',res.status)
    print('readback wire roundtrip',decode_record(encode_record(inp))==inp,decode_record(encode_record(res))==res)
    before=repo.load_attempt(ready.run_id)
    normalize(inp)
    print('attempt unchanged',before==repo.load_attempt(ready.run_id),repo.read_terminal(ready.run_id))
    for field in ('ready','checkpoint','parse_audit','tool_run','evidence_audits'):
        try:
            replace(inp.readback, **{field:None})
        except (ValueError,TypeError) as e:
            print('invalid readback field',field,type(e).__name__)
        else:
            print('ACCEPTED invalid readback',field)
