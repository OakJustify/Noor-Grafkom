"""JSON save manager."""

import json
import os


class SaveManager:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.expanduser("~/.noor")
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        self.settings_path = os.path.join(base_dir, "settings.json")
        self.progress_path = os.path.join(base_dir, "progress.json")

    def load_settings(self):
        try:
            with open(self.settings_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return {}

    def save_settings(self, data):
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_progress(self):
        try:
            with open(self.progress_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return {}

    def save_progress(self, data):
        with open(self.progress_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)