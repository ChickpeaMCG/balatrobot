import json
from datetime import datetime
from pathlib import Path


def cache_state(game_step, G):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    Path(f"gamestate_cache/{game_step}").mkdir(parents=True, exist_ok=True)
    filename = f"gamestate_cache/{game_step}/{timestamp}.json"
    with open(filename, "w") as f:
        f.write(json.dumps(G, indent=4))
