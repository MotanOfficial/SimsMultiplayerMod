"""Sims 4 multiplayer client mod (M1).

The package imports cleanly even when the game's `sims4` modules are not
available, so the networking/state layers can be unit tested on a regular
Python interpreter. Game hooks are only installed when `sims4` is importable.
"""

SIM4_AVAILABLE = False
try:
    import sims4  # noqa: F401

    SIM4_AVAILABLE = True
except Exception:  # pragma: no cover - game-only path
    SIM4_AVAILABLE = False

if SIM4_AVAILABLE:
    from simmp_client import sims4_plugin  # noqa: F401