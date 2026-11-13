"""Pure new-DTO writable-alias witness using a forged exact FrozenMap shell."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.net_annotation import AnnotationRef, MatchEvidence
from layauto_v2.normalization.net_annotation_codec import encode_record


def main():
    backing = [('supported', False), ('reason', 'unknown_policy')]
    policy = object.__new__(FrozenMap)
    object.__setattr__(policy, '_entries', backing)
    match = MatchEvidence(AnnotationRef('evidence', '1' * 64), (), (), (), (), policy, 'unsupported')
    before = encode_record(match)
    before_ref = match.ref.sha256
    backing.append(('external_mutation', True))
    after = encode_record(match)
    result = {'classification': 'pure-neutral-new-DTO-alias-witness-not-a-captured-build',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(), 'python': sys.version,
        'constructor_accepted_mutable_map_storage': True,
        'policy_identity_retained': match.policy is policy,
        'external_alias_changes_retained_policy': match.policy['external_mutation'] is True,
        'wire_changed': before != after, 'content_ref_changed': before_ref != match.ref.sha256,
        'wire_before_sha256': hashlib.sha256(before).hexdigest(), 'wire_after_sha256': hashlib.sha256(after).hexdigest(),
        'limitations': 'The FrozenMap shell was forged via object.__new__/object.__setattr__, not its safe public constructor; this tests the new boundary promise to reject malformed retained values before codecs copy them.'}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
