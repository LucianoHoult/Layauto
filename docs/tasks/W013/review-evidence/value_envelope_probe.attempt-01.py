"""Independent canonical Value primitive witness; not a W013/W010 cost run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, decode
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.publication_codec import encode_record, decode_record


def main():
    source = SourceFile('review-only.bin', bytes(range(256)))
    old_wire = encode_record(source)
    old_value = decode(old_wire)
    packet = canonical_bytes({'wire_schema': 'review-primitive/1', 'captured_input_wire': old_value})
    restored_value = decode(packet)['captured_input_wire']
    restored_wire = canonical_bytes(restored_value)
    assert restored_wire == old_wire
    assert decode_record(restored_wire) == source
    opaque_packet = canonical_bytes({'wire_schema': 'review-primitive/1', 'captured_input_wire': old_wire})
    assert len(packet) < len(opaque_packet)
    # Generic Value parsing is not capture authentication. A changed retained
    # SourceFile sha passes the algebra but fails the old public record decoder.
    bad_fields = dict(old_value['record']['fields'])
    bad_fields['sha256'] = FrozenMap({'scalar': '0' * 64})
    bad_record = FrozenMap({'record': 'SourceFile', 'fields': FrozenMap(bad_fields)})
    bad_value = FrozenMap({'wire_schema': old_value['wire_schema'], 'record': bad_record})
    try:
        decode_record(canonical_bytes(bad_value))
    except ValueError as exc:
        rejection = {'type': type(exc).__name__, 'message': str(exc)}
    else:
        raise AssertionError('old capture authentication did not reject changed sha')
    print(json.dumps({
        'classification': 'canonical-algebra-witness-only-not-W013-product-or-W010-cost',
        'python': sys.version,
        'old_record_type': 'SourceFile', 'old_wire_bytes': len(old_wire),
        'value_envelope_bytes': len(packet), 'opaque_bytes_envelope_bytes': len(opaque_packet),
        'value_envelope_overhead_bytes': len(packet) - len(old_wire),
        'opaque_envelope_overhead_above_double_bytes': len(opaque_packet) - 2 * len(old_wire),
        'old_wire_sha256': hashlib.sha256(old_wire).hexdigest(),
        'restored_wire_sha256': hashlib.sha256(restored_wire).hexdigest(),
        'old_public_decode_changed_sha_rejection': rejection,
        'plan_sha256': hashlib.sha256(Path('docs/tasks/W013/interface-plan.md').read_bytes()).hexdigest(),
        'limitations': 'No W010 Result or W013 implementation was built; no runtime/memory claim. Public old decode remains necessary.',
    }, indent=2))


if __name__ == '__main__':
    main()
