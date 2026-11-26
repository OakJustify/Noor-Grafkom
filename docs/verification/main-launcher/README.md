# `python main.py` launcher

## What was wrong

`nur_game` is not installed into `.venv-nur`; tests import it only because
`pytest.ini` sets `pythonpath = src`. A plain interpreter started in the
repository root could not import it, so there was no `python main.py` entry
point — `src/play_nur.py` was the only launcher and it needs `src` on the path.

## What was added

`main.py` at the project root:

- resolves `src/` from `Path(__file__).resolve().parent`, so it works from any
  working directory and without `PYTHONPATH`;
- mirrors the headless SDL environment setup for `--headless`, `--screenshot`
  and `--report`;
- delegates everything else to `nur_game.game.main`, so every existing option
  (`--menu`, `--continue`, `--dev`, `--fragment`, `--ending`, capture flags)
  behaves exactly as before.

## Verified by real execution

```text
$ python main.py --help                       -> usage, all options listed
$ python main.py --headless --frames 3 --mute --no-save \
      --screenshot … --report …               -> exit 0, 24450-byte PNG,
                                                  report: state=cutscene, region=1,
                                                  70 source hashes
$ (cwd = D:/) python …/main.py --help          -> usage (works from another dir)
$ python main.py --menu --headless --frames 2  -> exit 0
```

`tests/v4/test_main_launcher.py` (5 tests, written first and failing while
`main.py` was absent) asserts the wrapper exists, avoids `ModuleNotFoundError`
with `PYTHONPATH` stripped, lists `--dev/--menu/--ending/--fragment` in help,
produces a real headless frame and report, and runs from a different cwd.

Full suite result for this change: **498 passed** (`pytest.xml` in this folder;
declared = collected = 498, zero failures/errors/skips), including the 5 new
launcher tests, 7 pause-menu tests and 58 seated-arm tests.