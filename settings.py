"""Local settings override; empty starter configuration remains safe to open."""
import json,os
from pathlib import Path
BASE=Path(__file__).parent
def load_config():
 path=Path(os.getenv('CONFIG_PATH',str(BASE/'config/settings.json')))
 if not path.is_file():path=BASE/'config.json'
 return json.loads(path.read_text(encoding='utf-8'))
