"""Independent small checks of actual frozen A1 observers; not a benchmark."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path('/workspace/Layauto')
TOOL = ROOT/'docs/tasks/W012/A1/probe.py'
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('independent_a1_observer', TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
checks = 0


def check(condition, label):
    global checks
    assert condition, label
    checks += 1


def main():
    native = re.fullmatch
    try:
        for pattern in (r'(?:[0-9a-f]{2})*',r'[0-9a-f]*'):
            observer = module.RegexObserver(minimum=1)
            for value,flags in (('ab',0),('F0',0),('a',0),('AB',re.I)):
                expected = native(pattern,value,flags)
                with observer.active():
                    actual = re.fullmatch(pattern,value,flags)
                check(bool(actual) == bool(expected), 'existing match/nonmatch result')
                if expected:
                    check(actual.group() == expected.group(), 'existing matched text')
                check(re.fullmatch is native, 'original matcher restored')
            check(len(observer.events) == 4, 'only expected small observed values')
        for failure_type in (ValueError,TypeError,KeyError,KeyboardInterrupt,SystemExit):
            for suppression in (False,True):
                for pattern in (r'(?:[0-9a-f]{2})*',r'[0-9a-f]*'):
                    failure = failure_type('independent observer failure')
                    cause,context = RuntimeError('existing cause'),LookupError('existing context')
                    failure.__cause__,failure.__context__,failure.__suppress_context__ = cause,context,suppression
                    def fail(*args, **kwargs):
                        raise failure
                    re.fullmatch = fail
                    observer = module.RegexObserver(minimum=1)
                    try:
                        with observer.active():
                            re.fullmatch(pattern,'ab')
                    except BaseException as caught:
                        check(caught is failure and caught.__cause__ is cause and caught.__context__ is context
                              and caught.__suppress_context__ is suppression, 'exception object/cause/context/suppression')
                    else:
                        raise AssertionError('observer swallowed original fault')
                    check(re.fullmatch is fail and len(observer.events) == 1, 'fault observer restored')
                    re.fullmatch = native
        class ForeignPattern:
            def __ne__(self, other):
                raise AssertionError('observer invoked foreign pattern comparison')
        sentinel = object()
        def pass_through(*args, **kwargs):
            return sentinel
        re.fullmatch = pass_through
        observer = module.RegexObserver(minimum=1)
        with observer.active():
            check(re.fullmatch(ForeignPattern(),'ab') is sentinel, 'foreign pattern passed to original')
        check(not observer.events and re.fullmatch is pass_through, 'foreign pattern not observed')
    finally:
        re.fullmatch = native

    sys.path.insert(0,str(ROOT))
    from layauto_v2.domain import publication_codec
    from layauto_v2.domain.evidence import SourceRef
    from layauto_v2.domain.codec import canonical_bytes,decode
    value = SourceRef('independent-a1-review','a'*64)
    expected = publication_codec.encode_record(value)
    original_encode,original_decode = publication_codec.encode_record,publication_codec.decode_record
    meter = module.WireMeter()
    with meter.active():
        actual = publication_codec.encode_record(value)
        check(publication_codec.decode_record(actual) == value, 'meter public small roundtrip')
        check(decode(canonical_bytes(b'ab')) == b'ab', 'meter bytes roundtrip')
    check(actual == expected and not meter.stack, 'meter output unchanged')
    check(publication_codec.encode_record is original_encode and publication_codec.decode_record is original_decode,
          'meter entry functions restored')
    result = {'status':'passed','checks':checks,'probe_sha256':hashlib.sha256(TOOL.read_bytes()).hexdigest(),
              'scope':'Small actual frozen observers; original matches/flags/exception history/restoration, no large input or extra product encode'}
    (OUT/'hook-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
