import json
import os
from config import Config

class PlotManager:
    def __init__(self):
        self.file = Config.PLOT_FILE

    def get_state(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"chapter": 1, "scene": 1}

    def update_state(self, text_len):
        state = self.get_state()
        if text_len > 500:
            state["scene"] += 1
        if state["scene"] > 10:
            state["chapter"] += 1
            state["scene"] = 1
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return state