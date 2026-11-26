"""`python main.py` must launch the game from the project root.

nur_game is not installed into the virtual environment; pytest finds it only
because pytest.ini sets `pythonpath = src`.  A plain interpreter started in the
repository root therefore cannot import it, so the root launcher has to add
`src` itself and must work without any environment variable or `-m` switch.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / 'main.py'


def test_root_launcher_exists_and_is_a_thin_wrapper():
    assert MAIN.is_file(), 'the project root needs a main.py launcher'
    source = MAIN.read_text(encoding='utf-8')
    assert 'nur_game' in source
    # The launcher must locate src relative to itself, not the current directory.
    assert '__file__' in source


def test_root_launcher_adds_src_to_the_import_path():
    code = ('import runpy, sys; '
            f'sys.argv = ["main.py", "--help"]; '
            'ns = runpy.run_path(%r, run_name="__main__")' % str(MAIN))
    result = subprocess.run([sys.executable, '-c', code], cwd=str(ROOT),
                            capture_output=True, text=True, timeout=120,
                            env={k: v for k, v in os.environ.items()
                                 if k not in ('PYTHONPATH', 'PYTHONHOME')})
    assert 'No module named' not in result.stderr, result.stderr
    # --help raises SystemExit(0) after argparse prints the usage line.
    assert 'usage' in (result.stdout + result.stderr).lower()


@pytest.mark.parametrize('flag', ['--help'])
def test_launcher_runs_as_a_plain_python_script_without_pythonpath(flag):
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
    result = subprocess.run([sys.executable, str(MAIN), flag], cwd=str(ROOT),
                            capture_output=True, text=True, timeout=180, env=env)
    assert 'ModuleNotFoundError' not in result.stderr, result.stderr
    output = (result.stdout + result.stderr).lower()
    assert 'usage' in output
    for option in ('--dev', '--menu', '--ending', '--fragment'):
        assert option in output, f'{option} missing from the launcher help'


def test_launcher_headless_smoke_actually_runs_the_game(tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
    report = tmp_path/'report.json'
    shot = tmp_path/'frame.png'
    result = subprocess.run([sys.executable, str(MAIN), '--headless', '--frames', '2',
                             '--mute', '--no-save', '--report', str(report),
                             '--screenshot', str(shot)],
                            cwd=str(ROOT), capture_output=True, text=True, timeout=240, env=env)
    assert result.returncode == 0, result.stderr
    assert shot.is_file() and shot.stat().st_size > 1000
    import json
    data = json.loads(report.read_text(encoding='utf-8'))
    assert 'simulation' in data and 'sources' in data


def test_launcher_works_when_started_from_another_directory(tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
    result = subprocess.run([sys.executable, str(MAIN), '--help'], cwd=str(tmp_path),
                            capture_output=True, text=True, timeout=180, env=env)
    assert result.returncode == 0, result.stderr
    assert 'usage' in (result.stdout + result.stderr).lower()