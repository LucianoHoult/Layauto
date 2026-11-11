"""Derive finite cost tables from retained measurements, without running runtime."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path('/workspace/Layauto')
OUT = ROOT/'docs/tasks/W012'


def name(row):
    path = Path(row['file'])
    if path.is_file() and str(path).startswith(str(ROOT/'layauto_v2')):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and method.lineno == row['line']:
                        return node.name + '.' + method.name
    return row['function']


def main():
    result = {}
    for case in ('normal-direct','normal-readback','extraction-mismatch'):
        baseline = json.loads((OUT/('baseline-'+case+'.json')).read_text())
        profile = json.loads((OUT/('profile-'+case+'.json')).read_text())
        phases = json.loads((OUT/('profile-'+case+'.profile.json')).read_text())
        assert baseline['wire_sha256'] == profile['wire_sha256'] and baseline['wire_bytes'] == profile['wire_bytes']
        assert baseline['capture_sources'] == profile['capture_sources']
        stage = {}
        for phase, payload in phases.items():
            functions = []
            for row in payload['functions']:
                if row['file'].startswith(str(ROOT/'layauto_v2')) and (
                    row['function'] in ('__post_init__','_require_input','_evaluate','_analyze','normalize','validate_parse',
                                        'encode_record','decode_record','canonical_bytes','freeze','_wire','_decode','validate_closed_graph')
                ):
                    functions.append(dict(row, qualified_function=name(row)))
            stage[phase] = {'selected_functions':functions,
                            'top_exclusive':payload['functions'][:20],
                            'wire':payload['wire']}
        outer = 'normalization.channel_identity_codec.encode_record:ChannelIdentityResult'
        wire_stage = phases['W011_result_encode']['wire']
        hex_bytes = wire_stage['bytes_to_hex'][outer]['hex_characters']
        immediate = [row for row in wire_stage['edges'] if row['parent'] == outer]
        result[case] = {'baseline_wall_seconds':baseline['wall_seconds'],
                        'baseline_peak_rss_kib':baseline['process_peak_rss_kib'],
                        'wire_bytes':baseline['wire_bytes'],'wire_sha256':baseline['wire_sha256'],
                        'captures_count':len(baseline['capture_sources']),
                        'captures_bytes':sum(row['bytes'] for row in baseline['capture_sources']),
                        'outer_hex_characters':hex_bytes, 'outer_hex_fraction':hex_bytes/baseline['wire_bytes'],
                        'outer_nonhex_bytes':baseline['wire_bytes']-hex_bytes,
                        'immediate_nested_encode_outputs':immediate,
                        'result_graph':profile['result_graph'], 'decoded_result_graph':profile['decoded_result_graph'],
                        'explicit_retained_roots_graph':profile['retained_roots_graph'],
                        'profile_wall_seconds':profile['wall_seconds'], 'phases':stage}
    (OUT/'cost-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    for case,row in result.items():
        print(case, row['baseline_wall_seconds'], row['baseline_peak_rss_kib'],row['wire_bytes'],row['outer_hex_fraction'])
        print('BYTES', {key:row['result_graph'][key] for key in (
            'unique_objects','shallow_object_bytes','unique_bytes_objects','unique_bytes_payload',
            'content_unique_bytes_payload','logical_path_bytes_payload','equal_content_independent_bytes_extra')})
        print('NESTED',row['immediate_nested_encode_outputs'])


if __name__ == '__main__':
    main()
