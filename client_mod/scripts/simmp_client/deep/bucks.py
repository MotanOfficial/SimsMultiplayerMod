"""Bucks perk list / unlock / lock relays (Get Famous / Vampire / etc.).

Joiners relay perk-store UI intent; host owns bucks_tracker mutations.
Request-list replays original so Distributor fans via GameNetwork.
"""

from __future__ import division

from simmp.deep import (
    KIND_LOCK_ALL_PERKS,
    KIND_REQUEST_PERKS_LIST,
    KIND_UNLOCK_MULTIPLE_PERKS,
    KIND_UNLOCK_PERK,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION


def _relay_to_host(kind, body):
    wrapper = WrapperMessage(
        target_client=int(SESSION.host_player_id or 0),
        kind=kind,
        body=body,
    )
    return SESSION.send_wrapper(wrapper, route="host")


def _as_int(value, default=0):
    if value is None:
        return default
    try:
        return int(getattr(value, "value", getattr(value, "guid64", value)))
    except Exception:
        return default


def _as_bool(value):
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in ("1", "true", "yes", "on")


def _owner_id_or_none(owner_id):
    owner_id = int(owner_id or 0)
    return owner_id if owner_id > 0 else None


def _client_id():
    try:
        import services

        client = services.get_first_client()
        if client is None:
            return 0
        return int(getattr(client, "id", 0) or 0)
    except Exception:
        return 0


def _get_tracker(bucks_type, owner_id):
    try:
        from bucks.bucks_commands import get_bucks_tracker
        from bucks.bucks_enums import BucksType

        bt = BucksType(int(bucks_type))
        return get_bucks_tracker(
            bt,
            _owner_id_or_none(owner_id),
            _client_id(),
            True,
        )
    except Exception:
        return None


def _resolve_perk(perk_id):
    if not perk_id:
        return None
    try:
        from sims4.resources import Types
        from server_commands import argument_helpers

        return argument_helpers.get_tunable_instance(Types.BUCKS_PERK, str(int(perk_id)))
    except Exception:
        try:
            from sims4.resources import Types
            from server_commands import argument_helpers

            return argument_helpers.get_tunable_instance(Types.BUCKS_PERK, int(perk_id))
        except Exception:
            return None


def install_bucks_hooks():
    try:
        from bucks import bucks_commands
    except Exception:
        return False

    ok = False

    list_fn = getattr(bucks_commands, "request_perks_list", None)
    if list_fn is not None:

        @Override(list_fn, role=Role.JOINER)
        def _request_perks_list_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                bucks_type = _as_int(args[0] if args else kwargs.get("bucks_type"))
                owner_id = _as_int(args[1] if len(args) > 1 else kwargs.get("owner_id"))
                sort_by = _as_bool(
                    args[2] if len(args) > 2 else kwargs.get("sort_by_timestamp", False)
                )
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_REQUEST_PERKS_LIST,
                {
                    "bucks_type": bucks_type,
                    "owner_id": owner_id,
                    "sort_by_timestamp": sort_by,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    unlock_fn = getattr(bucks_commands, "unlock_perk_by_name_or_id", None)
    if unlock_fn is not None:

        @Override(unlock_fn, role=Role.JOINER)
        def _unlock_perk_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                bucks_perk = _as_int(args[0] if args else kwargs.get("bucks_perk"))
                unlock_free = _as_bool(
                    args[1] if len(args) > 1 else kwargs.get("unlock_for_free", False)
                )
                bucks_type = _as_int(
                    args[2] if len(args) > 2 else kwargs.get("bucks_type")
                )
                owner_id = _as_int(args[3] if len(args) > 3 else kwargs.get("owner_id"))
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_UNLOCK_PERK,
                {
                    "bucks_perk": bucks_perk,
                    "unlock_for_free": unlock_free,
                    "bucks_type": bucks_type,
                    "owner_id": owner_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    multi_fn = getattr(bucks_commands, "unlock_multiple_perks_with_buck_type", None)
    if multi_fn is not None:

        @Override(multi_fn, role=Role.JOINER)
        def _unlock_multiple_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                bucks_type = _as_int(args[0] if args else kwargs.get("bucks_type"))
                owner_id = _as_int(args[1] if len(args) > 1 else kwargs.get("owner_id"))
                unlock_free = _as_bool(
                    args[2] if len(args) > 2 else kwargs.get("unlock_for_free", False)
                )
                rest = list(args[3:]) if len(args) > 3 else list(kwargs.get("buck_perks") or [])
                buck_perks = [_as_int(p) for p in rest]
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_UNLOCK_MULTIPLE_PERKS,
                {
                    "bucks_type": bucks_type,
                    "owner_id": owner_id,
                    "unlock_for_free": unlock_free,
                    "buck_perks": buck_perks,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    lock_fn = getattr(bucks_commands, "lock_all_perks_for_bucks_type", None)
    if lock_fn is not None:

        @Override(lock_fn, role=Role.JOINER)
        def _lock_all_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                bucks_type = _as_int(args[0] if args else kwargs.get("bucks_type"))
                owner_id = _as_int(args[1] if len(args) > 1 else kwargs.get("owner_id"))
                refund = _as_bool(
                    args[2] if len(args) > 2 else kwargs.get("refund_cost", False)
                )
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_LOCK_ALL_PERKS,
                {
                    "bucks_type": bucks_type,
                    "owner_id": owner_id,
                    "refund_cost": refund,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


@MessageHandler(KIND_REQUEST_PERKS_LIST)
def _host_request_perks_list(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from bucks import bucks_commands
        from bucks.bucks_enums import BucksType

        bucks_type = BucksType(int(body.get("bucks_type") or 0))
        owner_id = _owner_id_or_none(body.get("owner_id"))
        sort_by = bool(body.get("sort_by_timestamp"))
        if owner_id is None:
            bucks_commands.request_perks_list(bucks_type, None, sort_by)
        else:
            bucks_commands.request_perks_list(bucks_type, owner_id, sort_by)
    except Exception:
        return


@MessageHandler(KIND_UNLOCK_PERK)
def _host_unlock_perk(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    tracker = _get_tracker(body.get("bucks_type"), body.get("owner_id"))
    if tracker is None:
        return
    perk = _resolve_perk(body.get("bucks_perk"))
    if perk is None:
        return
    try:
        if body.get("unlock_for_free"):
            tracker.unlock_perk(perk)
        else:
            tracker.pay_for_and_unlock_perk(perk)
    except Exception:
        return


@MessageHandler(KIND_UNLOCK_MULTIPLE_PERKS)
def _host_unlock_multiple_perks(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    tracker = _get_tracker(body.get("bucks_type"), body.get("owner_id"))
    if tracker is None:
        return
    free = bool(body.get("unlock_for_free"))
    for perk_id in body.get("buck_perks") or []:
        perk = _resolve_perk(perk_id)
        if perk is None:
            continue
        try:
            if free:
                tracker.unlock_perk(perk)
            else:
                tracker.pay_for_and_unlock_perk(perk)
        except Exception:
            continue


@MessageHandler(KIND_LOCK_ALL_PERKS)
def _host_lock_all_perks(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    tracker = _get_tracker(body.get("bucks_type"), body.get("owner_id"))
    if tracker is None:
        return
    try:
        from bucks.bucks_enums import BucksType

        bucks_type = BucksType(int(body.get("bucks_type") or 0))
        tracker.lock_all_perks(bucks_type, refund_cost=bool(body.get("refund_cost")))
    except Exception:
        return
