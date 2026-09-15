"""Run all simmp tests without third-party dependencies:

    python tests/run_tests.py

Works with the standard library unittest. The test modules are also
pytest-compatible.
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_SCRIPTS = os.path.join(ROOT, "client_mod", "scripts")
PROTOCOL_DIR = os.path.join(ROOT, "protocol")
for entry in (ROOT, PROTOCOL_DIR, CLIENT_SCRIPTS):
    if entry not in sys.path:
        sys.path.insert(0, entry)


def main():
    suite = unittest.defaultTestLoader.discover(
        start_dir=os.path.join(ROOT, "tests"),
        pattern="test_*.py",
    )
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())