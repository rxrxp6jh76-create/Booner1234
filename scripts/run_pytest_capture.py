#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print('Usage: run_pytest_capture.py <pytest-args...>')
    sys.exit(2)

args = ['python3', '-m', 'pytest'] + sys.argv[1:]
print('Running:', ' '.join(args))
res = subprocess.run(args, capture_output=True, text=True)
out_file = Path('scripts/pytest_capture.out')
out_file.write_text('--- STDOUT ---\n' + res.stdout + '\n--- STDERR ---\n' + res.stderr)
print('Wrote', out_file)
print('Return code', res.returncode)
sys.exit(res.returncode)
