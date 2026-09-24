"""Whim refresh/lock + satisfaction store relays.

Joiners relay whim UI intent; host mutates whim_tracker / satisfaction_tracker.
Reward-list rebuild fans via Distributor → GameNetwork.
"""

from __future__ import division

from simmp.deep import (
    KIND_REQUEST_SATISFACTION_REWARD_LIST,
    KIND_WHIM_REFRESH,
    KIND_WHIM_TOGGLE_LOCK,
    KIND_WHIMS_AWARD_PRIZE,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION
from simmp_client.deep import sim_select


def _relay_to_host(kind, body):
    wrapper = WrapperMessage(
        target_client=int(SESSION.host_player_id or 0),
        kind=kind,
        body=body,
    )
    return SESSION.send_wrapper(wrapper, route="host")


def _sim_id_from_arg(value):
    if value is None:
        return 0
    try:
        return int(getattr(value, "id", value))
    except Exception:
        return 0


def _active_sim_id_local():
    try:
        import services

        client = services.get_first_client()
        if client is None or getattr(client, "active_sim_info", None) is None:
            return 0
        return int(client.active_sim_info.id)
    except Exception:
        return 0


def install_whim_hooks():
    ok = False

    try:
        from server_commands import whim_commands
    except Exception:
        whim_commands = None

    if whim_commands is not None:
        refresh_fn = getattr(whim_commands, "refresh", None)
        if refresh_fn is not None:

            @Override(refresh_fn, role=Role.JOINER)
            def _refresh_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    whim = args[0] if args else kwargs.get("whim")
                    sim_id = _sim_id_from_arg(args[1] if len(args) > 1 else kwargs.get("sim_id"))
                    whim_id = int(getattr(whim, "guid64", whim) or 0)
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_WHIM_REFRESH,
                    {
                        "whim_id": whim_id,
                        "sim_id": sim_id,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        lock_fn = getattr(whim_commands, "toggle_lock", None)
        if lock_fn is not None:

            @Override(lock_fn, role=Role.JOINER)
            def _toggle_lock_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    whim = args[0] if args else kwargs.get("whim")
                    sim_id = _sim_id_from_arg(args[1] if len(args) > 1 else kwargs.get("sim_id"))
                    whim_id = int(getattr(whim, "guid64", whim) or 0)
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_WHIM_TOGGLE_LOCK,
                    {
                        "whim_id": whim_id,
                        "sim_id": sim_id,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

    try:
        from server_commands import sim_commands
    except Exception:
        sim_commands = None

    if sim_commands is not None:
        award_fn = getattr(sim_commands, "whims_award_prize", None)
        if award_fn is not None:

            @Override(award_fn, role=Role.JOINER)
            def _award_prize_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    reward_id = int(args[0] if args else kwargs.get("reward_id") or 0)
                except Exception:
                    return original(*args, **kwargs)
                sim_id = _active_sim_id_local()
                _relay_to_host(
                    KIND_WHIMS_AWARD_PRIZE,
                    {
                        "reward_id": reward_id,
                        "sim_id": sim_id,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        list_fn = getattr(sim_commands, "request_satisfaction_reward_list", None)
        if list_fn is not None:

            @Override(list_fn, role=Role.JOINER)
            def _request_list_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                sim_id = _active_sim_id_local()
                _relay_to_host(
                    KIND_REQUEST_SATISFACTION_REWARD_LIST,
                    {
                        "sim_id": sim_id,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

    return ok


def _resolve_whim(whim_id):
    if not whim_id:
        return None
    try:
        from sims4.resources import Types
        from server_commands import argument_helpers

        return argument_helpers.get_tunable_instance(Types.WHIM, whim_id)
    except Exception:
        return None


def _sim_info_from_id(sim_id):
    if not sim_id:
        return None
    try:
        import services

        info = services.sim_info_manager().get(sim_id)
        if info is not None:
            return info
        obj = services.object_manager().get(sim_id)
        if obj is not None:
            return getattr(obj, "sim_info", None)
    except Exception:
        return None
    return None


def _resolve_sim_info(body):
    sim_id = int(body.get("sim_id") or 0)
    info = _sim_info_from_id(sim_id)
    if info is not None:
        return info
    player_id = int(body.get("player_id") or 0)
    if player_id:
        return sim_select.get_active_sim_for_player(player_id)
    return None


@MessageHandler(KIND_WHIM_REFRESH)
def _host_whim_refresh(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    whim = _resolve_whim(int(body.get("whim_id") or 0))
    if whim is None:
        return
    try:
        import services

        sim_id = int(body.get("sim_id") or 0)
        sim = services.object_manager().get(sim_id) if sim_id else None
        if sim is None:
            return
        tracker = getattr(getattr(sim, "sim_info", None), "whim_tracker", None)
        if tracker is None:
            return
        tracker.refresh_whim(whim)
    except Exception:
        return


@MessageHandler(KIND_WHIM_TOGGLE_LOCK)
def _host_whim_toggle_lock(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    whim = _resolve_whim(int(body.get("whim_id") or 0))
    if whim is None:
        return
    try:
        import services

        sim_id = int(body.get("sim_id") or 0)
        sim = services.object_manager().get(sim_id) if sim_id else None
        if sim is None:
            return
        tracker = getattr(getattr(sim, "sim_info", None), "whim_tracker", None)
        if tracker is None:
            return
        tracker.toggle_whim_lock(whim)
    except Exception:
        return


@MessageHandler(KIND_WHIMS_AWARD_PRIZE)
def _host_whims_award_prize(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    reward_id = int(body.get("reward_id") or 0)
    if not reward_id:
        return
    info = _resolve_sim_info(body)
    if info is None:
        return
    try:
        tracker = getattr(info, "satisfaction_tracker", None)
        if tracker is None:
            return
        tracker.purchase_satisfaction_reward(reward_id)
        tracker.send_satisfaction_reward_list()
    except Exception:
        return


@MessageHandler(KIND_REQUEST_SATISFACTION_REWARD_LIST)
def _host_request_satisfaction_reward_list(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    info = _resolve_sim_info(body)
    if info is None:
        return
    try:
        tracker = getattr(info, "satisfaction_tracker", None)
        if tracker is None:
            return
        tracker.send_satisfaction_reward_list()
    except Exception:
        return