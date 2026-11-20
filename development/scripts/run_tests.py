"""Run the Python and frontend suites from any working directory."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log-dir', type=Path, default=ROOT / 'development/work/test-results',
                        help='Directory for separate Python and frontend logs')
    parser.add_argument('--coverage', action='store_true',
                        help='Measure Python coverage (requires the coverage package)')
    args = parser.parse_args()
    logs = args.log_dir.resolve()
    logs.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    env['PYTHONPATH'] = os.pathsep.join(filter(None, (str(ROOT / 'app'), env.get('PYTHONPATH'))))
    python = [sys.executable]
    if args.coverage:
        python += ['-m', 'coverage', 'run', '--source=app/itd',
                   '--data-file=' + str(logs / '.coverage')]
    suites = [
        ('python', python + ['-m', 'unittest', 'discover', '-s', 'development/tests', '-v'], ROOT),
        ('frontend', [shutil.which('npm') or 'npm', 'test'], ROOT / 'development/frontend'),
    ]
    failed = False
    for name, command, cwd in suites:
        path = logs / (name + '-tests.log')
        with path.open('w', encoding='utf-8') as output:
            try:
                result = subprocess.run(command, cwd=cwd, env=env, stdout=output,
                                        stderr=subprocess.STDOUT, check=False)
                code = result.returncode
            except OSError as error:
                output.write(str(error) + '\n')
                code = 1
        failed |= code != 0
        print(f'{name}: exit {code}; {path}', flush=True)
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
