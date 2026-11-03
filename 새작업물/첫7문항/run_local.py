"""Guarded local launcher. Keep this compatible with older Python for diagnostics."""
import os
from pathlib import Path
import sys
import traceback

def run():
    root = Path(__file__).resolve().parent
    os.chdir(root)
    if sys.version_info < (3, 10):
        print('Python 3.10 or newer is required. Current: ' + sys.version, file=sys.stderr)
        return 1
    try:
        if sys.argv[1:] == ['--test']:
            import unittest
            suite = unittest.defaultTestLoader.discover(str(root / 'tests'))
            return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
        from quick_survey.local_web import main
        return main()
    except Exception:
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    raise SystemExit(run())
