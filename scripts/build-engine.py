"""Build the native sidecar on the target OS with the current Python interpreter."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
assets = ['dashboard.html', 'dashboard.js', 'connections.js', 'dashboard.css', 'schema.json',
          'mysql-schema.sql', 'postgresql-schema.sql']
command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
           '--name', 'mock-source-engine', '--distpath', str(ROOT / 'build/engine'),
           '--workpath', str(ROOT / 'build/pyinstaller'), '--specpath', str(ROOT / 'build'),
           '--paths', str(ROOT / 'engine'), '--collect-all', 'pymysql', '--collect-all', 'psycopg2',
           '--collect-all', 'cryptography']
for asset in assets:
    command.extend(['--add-data', str(ROOT / 'engine' / asset) + ':.'])
command.append(str(ROOT / 'engine/desktop_entry.py'))
subprocess.run(command, cwd=ROOT, check=True)
