"""Per-player active sim tracking on the host."""

from simmp.deep import KIND_SET_ACTIVE_SIM, WrapperMessage
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.session import SESSION

# player_id -> sim_id
active_sims = {}


def get_active_sim_id_for_player(player_id):
    return active_sims.get(int(player_id))


def get_player_id_by_sim_id(sim_id):
    sim_id = int(sim_id)
    for player_id, active_id in active_sims.items():
        if active_id == sim_id:
            return player_id
    return None


def get_active_sim_for_player(player_id):
    sim_id = get_active_sim_id_for_player(player_id)
    if not sim_id:
        return None
    try:
        import services

        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return None
        return sim_info.get_sim_instance()
    except Exception:
        return None


def install_sim_select_hooks():
    try:
        from server.client import Client
    except Exception:
        return False

    method = getattr(Client, "_set_active_sim_without_field_distribution", None)
    if method is None:
        method = getattr(Client, "set_active_sim", None)
    if method is None:
        return False

    from simmp_client.deep.override import Override, Role

    @Override(method, role=Role.JOINER, target=Client, name=method.__name__)
    def _set_active_sim_joiner(original, self, sim_info, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(self, sim_info, *args, **kwargs)
        if sim_info is None:
            return original(self, sim_info, *args, **kwargs)
        wrapper = WrapperMessage(
            target_client=int(SESSION.host_player_id or 0),
            kind=KIND_SET_ACTIVE_SIM,
            body={
                "sim_id": int(sim_info.id),
                "player_id": int(SESSION.player_id or 0),
            },
        )
        SESSION.send_wrapper(wrapper, route="host")
        # Still update local UI selection so the joiner skewer feels responsive.
        try:
            return original(self, sim_info, *args, **kwargs)
        except Exception:
            return None

    @Override(method, role=Role.HOST, target=Client, name=method.__name__)
    def _set_active_sim_host(original, self, sim_info, *args, **kwargs):
        result = original(self, sim_info, *args, **kwargs)
        if SESSION.enabled and SESSION.is_host and sim_info is not None and SESSION.player_id is not None:
            active_sims[int(SESSION.player_id)] = int(sim_info.id)
        return result

    return True


@MessageHandler(KIND_SET_ACTIVE_SIM)
def _host_set_active_sim(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    sim_id = int(body.get("sim_id") or 0)
    if not player_id or not sim_id:
        return
    if active_sims.get(player_id) == sim_id:
        return
    previous = get_active_sim_for_player(player_id)
    active_sims[player_id] = sim_id
    # Autonomy flip for previous vs new active sim is applied when autonomy
    # settings for this player are disabled (see autonomy.py).
    try:
        from simmp_client.deep import autonomy as deep_autonomy

        deep_autonomy.apply_for_player(player_id, previous_sim=previous)
    except Exception:
        return
