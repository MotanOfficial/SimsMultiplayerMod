"""Adventure moment dialog routing (host) + joiner suppress.

Host owns AdventureMoment.run_adventure. Before the adventure dialog is shown,
waiting_for_callback_player_id is set from the adventure sim so GameNetwork
fans the dialog UI to the owning joiner. Joiners no-op local adventure runs.
"""

from __future__ import division

from simmp_client.deep import dialogs as deep_dialogs
from simmp_client.deep import sim_select
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION


def install_adventure_hooks():
    try:
        from interactions.utils.adventure import AdventureMoment
    except Exception:
        return False

    fn = getattr(AdventureMoment, "run_adventure", None)
    if fn is None:
        return False

    @Override(fn, role=Role.ALL, target=AdventureMoment, name="run_adventure")
    def _run_adventure(original, self, *args, **kwargs):
        if not SESSION.enabled:
            return original(self, *args, **kwargs)
        # Joiners never resolve adventure moments locally — host sim owns them.
        if not SESSION.is_host:
            return None
        prev = deep_dialogs.waiting_for_callback_player_id
        try:
            sim = getattr(self, "_sim", None)
            sim_id = getattr(sim, "id", None) if sim is not None else None
            if sim_id is not None:
                pid = sim_select.get_player_id_by_sim_id(int(sim_id))
                if pid is not None and int(pid) != int(SESSION.player_id or 0):
                    deep_dialogs.waiting_for_callback_player_id = int(pid)
            return original(self, *args, **kwargs)
        except Exception:
            try:
                return original(self, *args, **kwargs)
            except Exception:
                return None
        finally:
            deep_dialogs.waiting_for_callback_player_id = prev

    return True
