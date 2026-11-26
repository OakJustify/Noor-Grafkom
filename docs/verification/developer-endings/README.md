# Developer ending verification

Current source hashes and native launcher reports are in `verification.json`
and `launcher-{void,realworld,cards}.json`. This is separate from the earlier
six-fragment verification directory, whose reports refer to earlier sources.

- Full suite: 412 passed (`pytest.xml`), including 17 ending-preview tests.
- F7 starts CS07, F8 starts CS08, F9 starts the first closing card.
- Each stage was rendered and launched with `src/play_nur.py --dev --ending`.
- Automatic CS07 → CS08 → closing cards progression is covered by tests.
- Existing checkpoint bytes remain unchanged on preview, automatic completion,
  launcher exit, and QUIT; no-save remains forced for developer sessions.
- Story snapshots restore successfully; all memory entries are in the journal.
- Physics space/body identity stays the same, gameplay clocks and light charge
  are frozen during the finale, and F1 resets practice after any ending stage.
- At CS07 t=9.5 the actual surface has only RGB zero and audio is disabled.
  CS08 restores nonverbal audio according to the player's mute preference.

Captures: `key-void.png`, `void-pure-black.png`, `key-realworld.png`,
`key-cards.png`, `hud-shortcuts.png`, and the three native launcher PNGs.

The automated visual-review service returned HTTP 401, so no human-facing
composition/readability approval is claimed. Gameplay/cutscene artwork was not
changed by this feature; rendered frames and functional assertions are real.
