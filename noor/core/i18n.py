"""Internationalization: JSON string tables."""

import json
import os


class I18n:
    def __init__(self, base_dir=None, lang="id"):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "strings")
        self.base_dir = base_dir
        self.lang = lang
        self.strings = {}
        self._load(lang)

    def _path(self, lang):
        return os.path.join(self.base_dir, f"{lang}.json")

    def _load(self, lang):
        path = self._path(lang)
        try:
            with open(path, encoding="utf-8") as f:
                self.strings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self.strings = {}
        # fallback id
        if lang != "id" and not self.strings:
            self._load("id")

    def set_language(self, lang):
        self.lang = lang
        self._load(lang)

    def t(self, key, **fmt):
        val = self.strings.get(key)
        if val is None:
            # try fallback file
            try:
                with open(self._path("id"), encoding="utf-8") as f:
                    fb = json.load(f)
                val = fb.get(key, key)
            except Exception:  # noqa: BLE001
                val = key
        if fmt:
            try:
                val = val.format(**fmt)
            except Exception:  # noqa: BLE001, S110
                pass
        return val if val is not None else key

    def keys(self):
        return set(self.strings.keys())