"""Strict case-sensitive toy_literal_cdl/1 parser with exact lexeme evidence.

Written from the declared grammar. Legacy tokenization was inspected but its
float parsing, ignored records, implicit defaults and single-top collapse are
not carried into this implementation.
"""
from __future__ import annotations

import hashlib
import re
from fractions import Fraction
from typing import NoReturn

from layauto_v2.domain.codec import FrozenMap, freeze_map
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import Category, InputError
from ._access import exact, integer, mapping, sequence, string

_IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')
_POSITIVE = re.compile(r'[1-9][0-9]*\Z')
_LENGTH = re.compile(r'([1-9][0-9]*)n\Z')


def parse_cdl(source: SourceFile, tech: FrozenMap) -> FrozenMap:
    """Return all top documents; never compare source/target or admit NF=1."""
    formats = mapping(tech['formats'])
    profile = mapping(formats['cdl_dialect'])
    limits = mapping(formats['limits'])
    if profile['id'] != 'toy_literal_cdl/1':
        raise InputError('unsupported', 'UnsupportedCdlProfile', 'unimplemented CDL profile', source.ref())
    if len(source.data) > integer(limits['max_bytes_per_text_file']):
        raise InputError('parse', 'TextSizeExceeded', 'CDL text byte limit exceeded', source.ref())
    try:
        text = source.data.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise InputError('parse', 'InvalidTextEncoding', 'CDL is not UTF-8', source.ref(byte_offset=exc.start)) from exc
    models = mapping(mapping(tech['physical'])['models'])
    suffix = exact(mapping(profile['numeric_suffixes'])['n'])
    tops: list[dict[str, object]] = []
    names: set[str] = set()
    devices: list[dict[str, object]] = []
    device_names: set[str] = set()
    current_name: str | None = None
    current_pins: tuple[str, ...] = ()
    start_line = 0
    top_sources: dict[str, object] = {}
    record_count = 0
    offset = 0
    line_number = 1
    raw_line = ''

    def fail(code: str, message: str, category: Category = 'parse', column: int = 1) -> NoReturn:
        raise InputError(category, code, message, source.ref(line=line_number, column=column,
                         byte_offset=offset + len(raw_line[:column - 1].encode('utf-8'))))

    def identifier(value: str) -> None:
        if _IDENTIFIER.fullmatch(value) is None:
            fail('InvalidCdlIdentifier', f'unsupported identifier {value!r}', 'unsupported')

    def location(token: str, column: int) -> dict[str, object]:
        return {'uri': source.uri, 'sha256': source.sha256, 'line': line_number,
                'column': column, 'byte_offset': offset + len(raw_line[:column - 1].encode('utf-8')),
                'lexeme': token}

    for line_number, with_ending in enumerate(text.splitlines(keepends=True), 1):
        raw_line = with_ending.rstrip('\r\n')
        if any(ord(ch) < 32 and ch != '\t' for ch in raw_line):
            fail('InvalidCdlCharacter', 'control character outside CDL whitespace')
        stripped = raw_line.strip()
        if not stripped or stripped.startswith('*'):
            offset += len(with_ending.encode('utf-8'))
            continue
        record_count += 1
        if record_count > integer(limits['max_records']):
            fail('RecordLimitExceeded', 'CDL logical record limit exceeded')
        matches = list(re.finditer(r'\S+', raw_line))
        tokens = [match.group() for match in matches]
        first = tokens[0]
        if first == '.SUBCKT':
            if current_name is not None or len(tokens) < 2:
                fail('InvalidCdlStructure', 'nested or incomplete .SUBCKT')
            current_name = tokens[1]
            for token in tokens[1:]:
                identifier(token)
            if current_name in names or len(set(tokens[2:])) != len(tokens[2:]):
                fail('DuplicateCdlIdentity', 'duplicate top or ordered pin')
            names.add(current_name)
            current_pins = tuple(tokens[2:])
            devices, device_names = [], set()
            start_line = line_number
            top_sources = {'name': location(tokens[1], matches[1].start() + 1),
                           'pins': tuple(location(tokens[i], matches[i].start() + 1) for i in range(2, len(tokens)))}
        elif first == '.ENDS':
            if current_name is None or len(tokens) != 2 or tokens[1] != current_name:
                fail('InvalidCdlStructure', '.ENDS must match open .SUBCKT')
            tops.append({'name': current_name, 'pins': current_pins, 'globals': (),
                         'devices': devices, 'start_line': start_line, 'end_line': line_number,
                         'field_sources': top_sources})
            current_name = None
        elif first.startswith('.'):
            code = 'UnsupportedDependencyDirective' if first in ('.INCLUDE', '.LIB') else 'UnsupportedCdlDirective'
            fail(code, f'{first} is outside toy_literal_cdl/1', 'unsupported')
        else:
            if first.startswith('+'):
                fail('UnsupportedCdlContinuation', 'continuation is outside selected dialect', 'unsupported')
            if current_name is None or not first.startswith('M') or len(tokens) < 7:
                fail('InvalidCdlStructure', 'expected full MOS record inside .SUBCKT')
            for token in tokens[:6]:
                identifier(token)
            if first in device_names:
                fail('DuplicateCdlIdentity', f'duplicate device {first}')
            device_names.add(first)
            model_token = tokens[5]
            if model_token not in models:
                fail('UnsupportedCdlModel', f'undeclared model {model_token}', 'unsupported', matches[5].start() + 1)
            model = mapping(models[model_token])
            axes = mapping(model['parameter_axes'])
            required = tuple(string(item) for item in sequence(model['required_parameters']))
            parameters: dict[str, object] = {}
            for match in matches[6:]:
                token = match.group()
                column = match.start() + 1
                if token.count('=') != 1:
                    fail('InvalidCdlParameter', 'parameter must be NAME=literal', column=column)
                key, lexeme = token.split('=', 1)
                if key not in required:
                    fail('UnsupportedCdlParameter', f'unknown parameter {key}', 'unsupported', column)
                if key in parameters:
                    fail('DuplicateCdlParameter', f'duplicate parameter {key}', column=column)
                value: Fraction | str
                unit: str
                if key in ('NFIN', 'NF', 'M'):
                    if _POSITIVE.fullmatch(lexeme) is None:
                        code = 'UnsupportedCdlExpression' if any(c in lexeme for c in '{}()+*/') else 'InvalidCdlValue'
                        fail(code, f'{key} requires a positive integer literal', 'unsupported' if code.startswith('Unsupported') else 'parse', column)
                    try:
                        value, unit = Fraction(int(lexeme)), 'count'
                    except ValueError as exc:
                        raise InputError('parse', 'InvalidCdlValue', 'integer literal exceeds decoder capacity', source.ref(line=line_number, column=column)) from exc
                elif key in ('L', 'W'):
                    length = _LENGTH.fullmatch(lexeme)
                    if length is None:
                        code = 'UnsupportedCdlExpression' if any(c in lexeme for c in '{}()+*/') else 'InvalidCdlValue'
                        fail(code, f'{key} requires a positive integer with n suffix', 'unsupported' if code.startswith('Unsupported') else 'parse', column)
                    try:
                        value, unit = int(length.group(1)) * suffix, 'metres'
                    except ValueError as exc:
                        raise InputError('parse', 'InvalidCdlValue', 'length literal exceeds decoder capacity', source.ref(line=line_number, column=column)) from exc
                elif key == 'VT' and lexeme == 'toy':
                    value, unit = lexeme, 'token'
                else:
                    fail('InvalidCdlValue', f'unsupported literal for {key}', column=column)
                parameters[key] = {'lexeme': lexeme, 'exact': value, 'unit': unit,
                                   'axis': axes[key], 'source': location(token, column)}
            if set(parameters) != set(required):
                fail('MissingCdlParameter', 'record must explicitly provide every model parameter')
            devices.append({'name': first, 'model': model_token, 'terminals': tuple(tokens[1:5]),
                            'terminal_order': model['terminal_order'], 'parameters': parameters,
                            'line': line_number, 'source': location(raw_line, 1),
                            'field_sources': {label: location(tokens[i], matches[i].start() + 1)
                                              for i, label in enumerate(('name', 'D', 'G', 'S', 'B', 'model'))}})
        offset += len(with_ending.encode('utf-8'))
    if current_name is not None:
        fail('MissingCdlTerminator', 'open .SUBCKT missing .ENDS')
    if not tops:
        fail('MissingCdlTop', 'no .SUBCKT found')
    return freeze_map({'schema_version': 'layauto-cdl-evidence/1', 'dialect': profile['id'],
                       'tops': tops, 'globals': (), 'raw_document': source.data,
                       'source': {'uri': source.uri, 'sha256': source.sha256},
                       'dependency_closure': (), 'preprocess': 'none',
                       'empty_closure_sha256': hashlib.sha256(b'[]').hexdigest(),
                       'logical_record_count': record_count})
