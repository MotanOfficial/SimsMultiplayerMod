"""Per-player active sim tracking on the host."""

import time

from simmp.deep import KIND_SET_ACTIVE_SIM, WrapperMessage
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.session import SESSION

# player_id -> sim_id
active_sims = {}

_last_sync_sim_id = None
_last_sync_at = 0.0
_SYNC_INTERVAL = 1.0


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


def _notify_host_active_sim(sim_info):
    """Joiner -> host: register which sim this player is controlling."""
    if sim_info is None or not SESSION.enabled or SESSION.is_host:
        return
    if SESSION.host_player_id is None or SESSION.player_id is None:
        return
    wrapper = WrapperMessage(
        target_client=int(SESSION.host_player_id or 0),
        kind=KIND_SET_ACTIVE_SIM,
        body={
            "sim_id": int(sim_info.id),
            "player_id": int(SESSION.player_id or 0),
        },
    )
    SESSION.send_wrapper(wrapper, route="host")


def sync_active_sim_to_host():
    """Periodic joiner heartbeat so the host always knows our active sim.

    Open-source does this every 1s. Covers missed set_active_sim hooks and
    cases where UI selection updated without going through our Override.
    """
    global _last_sync_sim_id, _last_sync_at
    if not SESSION.enabled or SESSION.is_host:
        return
    now = time.time()
    if now - _last_sync_at < _SYNC_INTERVAL:
        return
    try:
        import services

        client = services.get_first_client()
        if client is None or client.active_sim_info is None:
            return
        sim_info = client.active_sim_info
        sim_id = int(sim_info.id)
    except Exception:
        return
    _last_sync_at = now
    _last_sync_sim_id = sim_id
    _notify_host_active_sim(sim_info)


def install_sim_select_hooks():
    try:
        from server.client import Client
    except Exception:
        return False

    from simmp_client.deep.override import Override, Role

    hooked = False
    # Hook both entry points — skewer may call either depending on pack/patch.
    for name in ("_set_active_sim_without_field_distribution", "set_active_sim"):
        method = getattr(Client, name, None)
        if method is None:
            continue

        def _make_joiner(method_name):
            @Override(
                getattr(Client, method_name),
                role=Role.JOINER,
                target=Client,
                name=method_name,
            )
            def _set_active_sim_joiner(original, self, sim_info, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(self, sim_info, *args, **kwargs)
                # Apply locally first so skewer / _active_sim_id() stay correct,
                # then tell the host (send_message local ViewUpdate now reaches
                # omega for SET_SIM_ACTIVE — see game_network).
                try:
                    result = original(self, sim_info, *args, **kwargs)
                except Exception:
                    result = None
                if sim_info is not None:
                    _notify_host_active_sim(sim_info)
                return result

            return _set_active_sim_joiner

        def _make_host(method_name):
            @Override(
                getattr(Client, method_name),
                role=Role.HOST,
                target=Client,
                name=method_name,
            )
            def _set_active_sim_host(original, self, sim_info, *args, **kwargs):
                result = original(self, sim_info, *args, **kwargs)
                if (
                    SESSION.enabled
                    and SESSION.is_host
                    and sim_info is not None
                    and SESSION.player_id is not None
                ):
                    active_sims[int(SESSION.player_id)] = int(sim_info.id)
                return result

            return _set_active_sim_host

        _make_joiner(name)
        _make_host(name)
        hooked = True

    return hooked


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
    try:
        from simmp_client.deep import autonomy as deep_autonomy

        deep_autonomy.apply_for_player(player_id, previous_sim=previous)
    except Exception:
        return
