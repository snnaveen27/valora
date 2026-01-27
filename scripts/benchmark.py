from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sanity_check


if __name__ == '__main__':
  sys.argv = ['sanity_check.py', '--benchmark'] + sys.argv[1:]
  raise SystemExit(sanity_check.main())
