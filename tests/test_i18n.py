import json
import os

from noor.core.i18n import I18n


def test_keys_identical():
    base = os.path.join("data", "strings")
    with open(os.path.join(base, "id.json"), encoding="utf-8") as f:
        idd = json.load(f)
    with open(os.path.join(base, "en.json"), encoding="utf-8") as f:
        enn = json.load(f)
    assert set(idd.keys()) == set(enn.keys())
    for v in idd.values():
        assert v.strip() != ""
    for v in enn.values():
        assert v.strip() != ""


def test_i18n_t():
    i = I18n(lang="id")
    assert i.t("ui.menu.start") != ""