"""Safe bounded YAML/JSON parsing, followed by explicit closed schema checks."""
from __future__ import annotations

import re
from collections.abc import Mapping

import yaml
from yaml.events import AliasEvent, CollectionEndEvent, CollectionStartEvent
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from layauto_v2.domain.codec import FrozenMap, freeze_map
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import InputError
from layauto_v2.tech.schema import SchemaError, validate_payload, validate_tech_payload

MAX_TEXT_BYTES = 1_000_000
MAX_DEPTH = 32
MAX_RECORDS = 1000


def load_document(source: SourceFile, *, max_bytes: int = MAX_TEXT_BYTES,
                  max_depth: int = MAX_DEPTH) -> FrozenMap:
    """Read no filesystem; parse these bytes once with exact scalar semantics.

    Bytes include whitespace/newlines. Only mappings/sequences add depth; the
    root container has depth one. Aliases and merge keys are outside the subset.
    """
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_TEXT_BYTES or type(max_depth) is not int or not 0 < max_depth <= MAX_DEPTH:
        raise ValueError('limits must tighten the layauto-input/1 bootstrap ceiling')
    if len(source.data) > max_bytes:
        raise InputError('config', 'SizeLimitExceeded', f'text exceeds {max_bytes} bytes', source.ref())
    try:
        text = source.data.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise InputError('parse', 'InvalidEncoding', 'expected UTF-8 text', source.ref(byte_offset=exc.start)) from exc
    try:
        depth = 0
        for event in yaml.parse(text, Loader=yaml.SafeLoader):
            if isinstance(event, AliasEvent):
                assert event.start_mark is not None
                raise InputError('unsupported', 'UnsupportedAlias', 'YAML aliases are outside the safe subset', source.ref(line=event.start_mark.line + 1, column=event.start_mark.column + 1))
            if isinstance(event, CollectionStartEvent):
                depth += 1
                if depth > max_depth:
                    assert event.start_mark is not None
                    raise InputError('config', 'DepthLimitExceeded', f'container depth exceeds {max_depth}', source.ref(line=event.start_mark.line + 1, column=event.start_mark.column + 1))
            elif isinstance(event, CollectionEndEvent):
                depth -= 1
        node = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.MarkedYAMLError as exc:
        mark = exc.problem_mark
        ref = source.ref(line=mark.line + 1, column=mark.column + 1) if mark is not None else source.ref()
        raise InputError('parse', 'InvalidDocumentSyntax', str(exc), ref) from exc
    except yaml.YAMLError as exc:
        raise InputError('parse', 'InvalidDocumentSyntax', str(exc), source.ref()) from exc
    if node is None:
        raise InputError('config', 'EmptyDocument', 'document is empty', source.ref())

    def error(n: Node, code: str, message: str) -> InputError:
        return InputError('config', code, message, source.ref(line=n.start_mark.line + 1, column=n.start_mark.column + 1))

    def string_value(n: ScalarNode) -> str:
        # PyYAML leaves JSON UTF-16 escapes as separate surrogate code points.
        # Decode pairs before key comparison; never retain an unpaired surrogate
        # in a value that will later be encoded as canonical UTF-8 evidence.
        chars: list[str] = []
        index = 0
        while index < len(n.value):
            code = ord(n.value[index])
            if 0xD800 <= code <= 0xDBFF:
                if index + 1 == len(n.value) or not 0xDC00 <= ord(n.value[index + 1]) <= 0xDFFF:
                    raise error(n, 'InvalidUnicodeScalar', 'high surrogate requires a following low surrogate')
                low = ord(n.value[index + 1])
                chars.append(chr(0x10000 + ((code - 0xD800) << 10) + low - 0xDC00))
                index += 2
            elif 0xDC00 <= code <= 0xDFFF:
                raise error(n, 'InvalidUnicodeScalar', 'low surrogate requires a preceding high surrogate')
            else:
                chars.append(n.value[index])
                index += 1
        return ''.join(chars)

    def build(n: Node) -> object:
        if isinstance(n, MappingNode) and n.tag == 'tag:yaml.org,2002:map':
            result: dict[str, object] = {}
            for key_node, value_node in n.value:
                key = build(key_node)
                if type(key) is not str:
                    raise error(key_node, 'InvalidKeyType', 'mapping keys must be strings')
                assert isinstance(key, str)
                if key in result:
                    raise error(key_node, 'DuplicateKey', f'duplicate key: {key}')
                result[key] = build(value_node)
            return result
        if isinstance(n, SequenceNode) and n.tag == 'tag:yaml.org,2002:seq':
            return [build(item) for item in n.value]
        if isinstance(n, ScalarNode):
            if n.tag == 'tag:yaml.org,2002:str':
                # YAML does not recognize every JSON nonfinite/numeric token.
                if n.style is None and (n.value in ('NaN', 'Infinity', '-Infinity') or re.fullmatch(r'[-+]?[0-9]+(?:\.[0-9]*)?[eE][-+]?[0-9]+', n.value)):
                    raise error(n, 'NonExactNumber', 'numeric input requires an integer or explicit exact representation')
                return string_value(n)
            if n.tag == 'tag:yaml.org,2002:null':
                return None
            if n.tag == 'tag:yaml.org,2002:bool':
                if n.value.lower() not in ('true', 'false'):
                    raise error(n, 'InvalidBoolean', 'booleans must use true/false')
                return n.value.lower() == 'true'
            if n.tag == 'tag:yaml.org,2002:int':
                if re.fullmatch(r'(?:0|-[1-9][0-9]*|[1-9][0-9]*)', n.value) is None:
                    raise error(n, 'InvalidInteger', 'integer must use canonical decimal spelling')
                try:
                    return int(n.value)
                except ValueError as exc:
                    raise error(n, 'InvalidInteger', 'integer exceeds interpreter digit limit') from exc
            if n.tag == 'tag:yaml.org,2002:float':
                raise error(n, 'NonExactNumber', 'float/NaN/Infinity are forbidden')
        raise error(n, 'UnsupportedTag', f'unsupported YAML tag: {n.tag}')

    value = build(node)
    if not isinstance(value, dict):
        raise error(node, 'InvalidRootType', 'document root must be an object')
    return freeze_map(value)


def validate_document(doc: FrozenMap, kind: str, source: SourceFile) -> None:
    try:
        validate_payload(doc, kind)
    except SchemaError as exc:
        raise InputError('config', exc.code, str(exc), source.ref(field=exc.path)) from exc


def validate_tech(tech: FrozenMap, sources: Mapping[str, SourceFile]) -> None:
    try:
        validate_tech_payload(tech)
    except SchemaError as exc:
        owner = exc.path.strip('/').split('/')[0]
        source = sources.get(owner)
        if source is None:
            source = next(iter(sources.values()))
        raise InputError('config', exc.code, str(exc), source.ref(field=exc.path)) from exc
