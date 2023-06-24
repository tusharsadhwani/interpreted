"""CLI interface for interpreted."""
import argparse
import sys

from interpreted.interpreter import interpret


def cli() -> int:
    """CLI interface."""
    parser = argparse.ArgumentParser()
    parser.add_argument("filepath", nargs="?")

    args = parser.parse_args()

    if args.filepath is None:
        code = sys.stdin.read()
    else:
        try:
            with open(args.filepath) as file:
                code = file.read()

        except OSError:
            print(
                f"\033[31mError:\033[m Unable to open file: {args.filepath!r}",
                file=sys.stderr,
            )
            return 1

    interpret(code)
    return 0
