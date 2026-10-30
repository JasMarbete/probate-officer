"""Interpret one email and print the CCD actions it would plan. Dry run: nothing is sent or changed.

Usage:
  python scripts/interpret_email.py --file email.txt
  echo "case reference ... " | python scripts/interpret_email.py
"""

import argparse
import json
import sys
from pathlib import Path

# Make the project root importable, so `import officer` works from any folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from officer.intake import email_reader


def main(argv=None):
    parser = argparse.ArgumentParser(description="Dry-run interpretation of one email.")
    parser.add_argument("--file", help="a text file holding the email body; reads stdin if omitted")
    args = parser.parse_args(argv)
    text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()

    print("DRY RUN: nothing is sent and CCD is not changed.", file=sys.stderr)
    print(json.dumps(email_reader.interpret(text), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
