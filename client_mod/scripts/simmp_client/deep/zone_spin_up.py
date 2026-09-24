"""Joiner zone spin-up: force batch sim spawning locally.

Concept from open-source CLIENT override on SimSpawnerService —
joiners spawn all pending sims immediately during zone load instead of
trickling, so the lot is ready when host simulation is already running.
"""

from __future__ import division

from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION


def install_zone_spin_up_hooks():
    try:
        from sims.sim_spawner_service import SimSpawnerService, _SpawningMode
    except Exception:
        try:
            from sims.sim_spawner_service import SimSpawnerService
            _SpawningMode = None
        except Exception:
            return False

    fn = getattr(SimSpawnerService, "batch_spawn_during_zone_spin_up", None)
    if fn is None:
        return False

    @Override(fn, role=Role.JOINER)
    def _batch_spawn_joiner(original, self, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(self, *args, **kwargs)
        try:
            if _SpawningMode is not None:
                self._mode = _SpawningMode.BATCH_SPAWNING
            done = False
            while not done:
                try:
                    done = not self._spawn_next_sim()
                except Exception:
                    done = True
            if not getattr(self, "_spawning_requests", None):
                if _SpawningMode is not None:
                    self._mode = _SpawningMode.WAITING_HITTING_MARKS
            elif _SpawningMode is not None:
                self._mode = _SpawningMode.WAITING_HITTING_MARKS
            return None
        except Exception:
            return original(self, *args, **kwargs)

    return True
