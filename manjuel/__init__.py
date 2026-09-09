"""manjuel -- local multi-agent pipeline driven by agents.md."""

__version__ = "0.1.6"

# THE OLD DIALS STILL TURN. Renamed from chainkit 2026-09-09 at the
# operator's word. Twenty-two CHAINKIT_* names are documented in RUNBOOK's
# dial table and may sit in a .env or a shell that predates the rename; a
# dial that silently stops working is worse than one that is gone. Each is
# honoured once, at import, and only when its MANJUEL_ twin is unset.
def _carry_old_dials():
    import os
    carried = []
    for k, v in list(os.environ.items()):
        if not k.startswith('CHAINKIT_'):
            continue
        new = 'MANJUEL_' + k[len('CHAINKIT_'):]
        if not os.environ.get(new):
            os.environ[new] = v
            carried.append(k)
    return carried


OLD_DIALS_CARRIED = _carry_old_dials()
