
import json, os
from typing import Any, Dict

class Memory:
    def __init__(self, path: str):
        self.path = path
        self.data = {"turns": [], "state": {}}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                pass
    def save_turn(self, user: str, answer: str, evc_info: Dict[str, Any], reflect_vec: Dict[str, float]):
        self.data["turns"].append({"user": user, "answer": answer, "evc": evc_info, "reflection": reflect_vec})
        self.data["state"]["E"] = evc_info.get("E", 0.5)
        self.data["state"]["phase"] = evc_info.get("phase", "calm")
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
