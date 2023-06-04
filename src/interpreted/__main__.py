"""Support executing the CLI by doing `python -m interpreted`."""
from interpreted.cli import cli

if __name__ == "__main__":
    raise SystemExit(cli())
