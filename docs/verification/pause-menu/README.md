# Pause → main menu verification

The pause screen now offers a third action alongside resume and retry:

```text
ISTIRAHAT
ESC kembali bermain · R kembali ke stasiun terakhir
B simpan & kembali ke menu utama
Cahaya dan napas berhenti berkurang saat istirahat.
```

## Behaviour

- `B` (or `Game.return_to_menu()`) only works while paused; elsewhere it is inert
  and leaves the snapshot unchanged.
- The checkpoint is written **first**, so the run stays available: `C` at the
  menu resumes the exact position, `ENTER` starts a new journey.
- World, story, lantern, stamina and camera are untouched; only the screen state
  becomes `menu`. The world/story snapshot is compared with the `state` field
  excluded, because that field legitimately changes.
- A developer practice session is ended on return, and the original persistence
  option is restored, so a normal `C` afterwards behaves like any other menu.
- An existing save file is not rewritten by merely leaving for the menu and
  quitting.

## Evidence

- `pause.png` — the real pause overlay with the new line, fully readable.
- `after-return-menu.png` — the frame immediately after pressing B.
- `pytest.xml` — full suite run.
- `verification.json` — current source hashes plus the assertions above.

Tests live in `tests/v4/test_story_pause_menu.py` and were written before the
feature: all seven failed against the old pause screen.