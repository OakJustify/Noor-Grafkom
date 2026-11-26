# Developer menu button verification

The native `src/play_nur.py --menu` launcher was executed without `--dev`.
`launcher.json` and `verification.json` contain current-source hashes.

- Full suite: 428 passed (`pytest.xml`), including 16 developer-menu tests.
- Left-click and D start a fresh unsaved session near F01; F7–F9 then work.
- Button drawing, label width, and hover feedback were exercised.
- Click coordinates work at 960×540, 1280×720, and 480×270 display sizes.
- Unrelated clicks and gameplay D input do not activate developer mode.
- Existing checkpoint bytes were unchanged by menu launch and practice exit.
- Normal Enter/Space restores the original persistence option, including
  `--no-save`; C resumes the original campaign without leaking practice state.
- Failed C followed by QUIT cannot overwrite an invalid existing checkpoint.

Captures: `menu.png`, `menu-960x540.png`, `menu-1280x720.png`,
`menu-480x270.png`, and `after-click.png`.

The visual-review service returned HTTP 401. Captures and functional/geometry
checks are verified, but no pixel-based readability/composition approval is
claimed. The captures remain available for human inspection.
