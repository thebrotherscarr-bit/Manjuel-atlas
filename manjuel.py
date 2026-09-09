#!/usr/bin/env python3
"""Entrypoint. Real implementation lives in manjuel/.

    python manjuel.py                        the REPL, on this ground
    python manjuel.py --headless             the same sitting over stdin/stdout
                                           as JSON lines (manjuel/serve.py)
    python manjuel.py --ground worlds/NAME   either of the above, sitting INSIDE
                                           a world: its own agents/, skills/,
                                           sessions/, logs/ -- the origin's
                                           record untouched
    python manjuel.py --help | --version     printed here; nothing is opened

THE ARGV IS READ BEFORE ANY DOOR IS CHOSEN, and an unknown flag is REFUSED BY
NAME. This door used to accept anything and do the default, which cost three
different things (found 2026-09-09 at the operator's "what is it missing?"):
`--help` fell through and opened a sitting and loaded models; `--heedless`
silently gave the interactive REPL instead of the headless one; and `--gound
worlds/x` silently ran on the estate's own record instead of the world he
named. An unknown flag is never a request to do the default thing.

The contract itself lives in manjuel/cli.py beside the flag vocabulary, so a
stroke can hold it to its word. This file stays a launcher: it asks, it prints,
it exits.
"""

import sys

if __name__ == "__main__":
    try:
        from manjuel import __version__
        from manjuel.cli import USAGE, read_argv

        try:
            mode = read_argv(sys.argv[1:])
        except ValueError as exc:
            print(f"\n  refused: {exc}\n", file=sys.stderr)
            sys.exit(2)

        if mode == "help":
            print(USAGE)
            sys.exit(0)
        if mode == "version":
            print(f"manjuel {__version__}")
            sys.exit(0)

        if mode == "headless":
            from manjuel.serve import main
        else:
            from manjuel.cli import main
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
