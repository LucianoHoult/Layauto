"""CR-01-FR1: accepted query token whitespace keeps typed swap admission."""
from pathlib import Path
import sys
import tempfile
REPOSITORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY))
sys.path.insert(0, str(REPOSITORY / 'tests/contracts'))
from w005_cases import copy_input, without_cache, rebind
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result, normalize

with tempfile.TemporaryDirectory() as directory:
    root = copy_input(Path(directory))
    without_cache(root)
    path = root / 'query/raw/iXref.temp'
    path.write_text(path.read_text().replace('0 Q17 0 MN0', '0 Q17 0 MN0\tX'))
    rebind(root)
    parsed = read_inputs(root / 'site_config.yaml')
    print('reader', parsed.status, parsed.issues)
    try:
        result = normalize(from_parse_result(parsed))
        print('normalization', result.status, [issue.code for issue in result.issues])
    except Exception as exc:
        print('normalization raised', type(exc).__name__, str(exc))
