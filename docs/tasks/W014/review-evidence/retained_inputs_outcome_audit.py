"""Check CR10/11 preserved actual before/after evidence without product calls."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent

def read(name):
 text=(P/name).read_text()
 return json.loads(text[text.index('{'):])

before=read('retained_draft_inputs_probe.before.stdout.txt')
after=read('retained_draft_inputs_extended_probe.after.stdout.txt')
assert before['cases'][0]['accepted'] is True
assert before['cases'][1]['error_type']=='KeyError'
assert len(after['cases'])==6 and all(r['rejected'] and r['error_type']=='ValueError' for r in after['cases'])
print(json.dumps({'findings':['CR10','CR11'],'before_after_status':'passed','after_codec_sha256':after['codec_sha256']}))
