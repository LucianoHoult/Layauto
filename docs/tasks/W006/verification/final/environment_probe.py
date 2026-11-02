import importlib.metadata,json,platform,sys
from pathlib import Path
import layauto_v2
print(json.dumps({'python':sys.version,'executable':sys.executable,'prefix':sys.prefix,'platform':platform.platform(),'import_path':str(Path(layauto_v2.__file__).resolve()),'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}},indent=2,sort_keys=True))
