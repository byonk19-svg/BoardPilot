import json
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def test_compile_command_uses_supplied_baseline():
    environment = dict(os.environ, PYTHONPATH=str(ROOT/'services/api/src'), PYTHONUTF8='1')
    result = subprocess.run([sys.executable,'-m','woodwork.cli','compile',str(ROOT/'tests/fixtures/bookcase-baseline.json')],cwd=ROOT,env=environment,capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stderr
    ledger = json.loads(result.stdout)
    assert ledger['part_instance_count'] == 7
    assert ledger['inside_width_mm'] == '726'
    assert ledger['canonical_spec_sha256'] == '2d4c00c1478a2cc839f2c3a32bbd6d2072196de2e0f8cb736ab08d9d3560aa2b'
