"""Independent regression witness: checked and retained collection differ."""
import json
import subprocess
from layauto_v2.domain.evidence import EvidenceRecord, SourceFile
from layauto_v2.domain.results import ParseResult

class Flip(list):
    def __init__(self, value):
        super().__init__([value])
        self.count = 0
    def __iter__(self):
        self.count += 1
        return list.__iter__(self) if self.count == 1 else iter([None])

source = SourceFile('independent-source', b'x')
result = {'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'observations':[]}
for name, call in (
    ('EvidenceRecord.sources', lambda:EvidenceRecord('example',{},Flip(source.ref()))),
    ('ParseResult.sources', lambda:ParseResult('success',{},(),(),Flip(source))),
):
    try:
        record = call()
    except Exception as error:
        result['observations'].append(dict(entry=name,outcome='raised',type=type(error).__name__,message=str(error)))
    else:
        result['observations'].append(dict(entry=name,outcome='accepted',retained_sources_repr=repr(record.sources),retained_invalid_none=any(item is None for item in record.sources)))
print(json.dumps(result,indent=2))
