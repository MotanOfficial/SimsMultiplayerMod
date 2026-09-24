"""Disable local Timeline.simulate on joiners (host owns the sim)."""

from simmp_client.deep.override import Override, Role


def install_timeline_hooks():
    try:
        from scheduling import Timeline
    except Exception:
        return False

    @Override(Timeline.simulate, role=Role.JOINER, enabled_while_traveling=False)
    def _simulate_joiner(original, *args, **kwargs):
        # Host runs the only live simulation. Joiners stay frozen at the
        # scheduling layer and receive state via GameNetworkMessage / omega.
        return None

    return True
