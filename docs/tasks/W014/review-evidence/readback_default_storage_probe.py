"""Legitimate old publication discriminators are class-held dataclass defaults."""
from dataclasses import fields
import hashlib
import json
from pathlib import Path
from layauto_v2.domain.publication import RunRequest,RunAttempt
from layauto_v2.domain.terminal_relations import validate_terminal_graph

request=RunRequest('review-run','review-lineage','review-key','/tmp/review/site_config.yaml')
attempt=RunAttempt(request)
results=[]
for obj in (request,attempt):
 row={'type':type(obj).__name__,'class_default_fields':[f.name for f in fields(obj) if f.name not in vars(obj)]}
 try:validate_terminal_graph(obj,(RunRequest,RunAttempt))
 except ValueError as exc:row.update(accepted=False,error=str(exc))
 else:row.update(accepted=True)
 results.append(row)
print(json.dumps({'domain_sha256':hashlib.sha256(Path('layauto_v2/domain/terminal_relations.py').read_bytes()).hexdigest(),'results':results},indent=2))
