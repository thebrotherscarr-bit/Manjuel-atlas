#!/usr/bin/env python3
"""Entrypoint. Real implementation lives in chainkit/.

    python chain.py                        the REPL, on this ground
    python chain.py --headless             the same sitting over stdin/stdout
                                           as JSON lines (chainkit/serve.py)
    python chain.py --ground worlds/NAME   either of the above, sitting INSIDE
                                           a world: its own agents/, skills/,
                                           sessions/, logs/ -- the origin's
                                           record untouched
"""

import sys

if __name__ == "__main__":
    try:
        if "--headless" in sys.argv[1:]:
            from chainkit.serve import main
        else:
            from chainkit.cli import main
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
