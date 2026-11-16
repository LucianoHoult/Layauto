"""A W014 leaf envelope cannot promote arbitrary old registry root records."""
from dataclasses import fields
import json
from layauto_v2.domain.codec import canonical_bytes
from layauto_v2.domain.publication import RunRequest
from layauto_v2.normalization import terminal_relations_codec as codec
obj=RunRequest('r','l','k','/tmp/site.yaml')
legacy_record={'record':'RunRequest','fields':{field.name:codec._pack(getattr(obj,field.name)) for field in fields(obj)}}
packet=canonical_bytes({'wire_schema':codec.WIRE_VERSION,'kind':'record','record':legacy_record})
try:codec.decode_record(packet)
except BaseException as exc:print(json.dumps({'foreign_root':'RunRequest','error_type':type(exc).__name__,'message':str(exc)}))
else:raise AssertionError('Foreign root accepted')
