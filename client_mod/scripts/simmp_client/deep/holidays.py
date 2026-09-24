"""Holiday calendar relays (Seasons): get/add/update/remove.

Joiners relay calendar UI intent; host owns holiday_service mutations.
Get-data commands replay on the host so Distributor ops fan via GameNetwork.
"""

from __future__ import division

from simmp.deep import (
    KIND_ADD_HOLIDAY,
    KIND_GET_ACTIVE_HOLIDAY_DATA,
    KIND_GET_HOLIDAY_DATA,
    KIND_REMOVE_HOLIDAY,
    KIND_UPDATE_HOLIDAY,
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


def _sim_id_from_arg(value):
    if value is None:
        return 0
    try:
        return int(getattr(value, "id", value))
    except Exception:
        return 0


def install_holiday_hooks():
    try:
        from holidays import holiday_commands
    except Exception:
        return False

    ok = False

    get_fn = getattr(holiday_commands, "get_holiday_data", None)
    if get_fn is not None:

        @Override(get_fn, role=Role.JOINER)
        def _get_holiday_data_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                holiday_id = int(args[0]) if args else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_GET_HOLIDAY_DATA,
                {
                    "holiday_id": holiday_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    get_active_fn = getattr(holiday_commands, "get_active_holiday_data", None)
    if get_active_fn is not None:

        @Override(get_active_fn, role=Role.JOINER)
        def _get_active_holiday_data_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                sim_id = _sim_id_from_arg(args[0] if args else None)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_GET_ACTIVE_HOLIDAY_DATA,
                {
                    "sim_id": sim_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    update_fn = getattr(holiday_commands, "update_holiday", None)
    if update_fn is not None:

        @Override(update_fn, role=Role.JOINER)
        def _update_holiday_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                holiday_data = args[0] if args else kwargs.get("holiday_data")
                data_s = str(holiday_data) if holiday_data is not None else ""
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_UPDATE_HOLIDAY,
                {
                    "holiday_data": data_s,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    add_fn = getattr(holiday_commands, "add_holiday", None)
    if add_fn is not None:

        @Override(add_fn, role=Role.JOINER)
        def _add_holiday_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                holiday_data = args[0] if args else None
                season = args[1] if len(args) > 1 else 0
                day = args[2] if len(args) > 2 else 0
                data_s = str(holiday_data) if holiday_data is not None else ""
                season_i = int(getattr(season, "value", season) or 0)
                day_i = int(day) if day is not None else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_ADD_HOLIDAY,
                {
                    "holiday_data": data_s,
                    "season_type": season_i,
                    "day": day_i,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    remove_fn = getattr(holiday_commands, "remove_holiday", None)
    if remove_fn is not None:

        @Override(remove_fn, role=Role.JOINER)
        def _remove_holiday_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                holiday_id = int(args[0]) if args else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_REMOVE_HOLIDAY,
                {
                    "holiday_id": holiday_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


def _parse_holiday_pb(data_s):
    try:
        from google.protobuf import text_format
        from protocolbuffers import GameplaySaveData_pb2

        holiday = GameplaySaveData_pb2.Holiday()
        text_format.Merge(data_s or "", holiday)
        return holiday
    except Exception:
        return None


@MessageHandler(KIND_GET_HOLIDAY_DATA)
def _host_get_holiday_data(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    holiday_id = int(body.get("holiday_id") or 0)
    try:
        from holidays import holiday_commands

        holiday_commands.get_holiday_data(holiday_id)
    except Exception:
        return


@MessageHandler(KIND_GET_ACTIVE_HOLIDAY_DATA)
def _host_get_active_holiday_data(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    try:
        from holidays import holiday_commands

        if sim_id:
            holiday_commands.get_active_holiday_data(sim_id)
        else:
            holiday_commands.get_active_holiday_data()
    except Exception:
        return


@MessageHandler(KIND_UPDATE_HOLIDAY)
def _host_update_holiday(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    data = _parse_holiday_pb(body.get("holiday_data") or "")
    if data is None:
        return
    try:
        import services

        svc = services.holiday_service()
        if svc is None:
            return
        svc.modify_holiday(data)
    except Exception:
        return


@MessageHandler(KIND_ADD_HOLIDAY)
def _host_add_holiday(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    data = _parse_holiday_pb(body.get("holiday_data") or "")
    if data is None:
        return
    try:
        import services

        svc = services.holiday_service()
        if svc is None:
            return
        season = int(body.get("season_type") or 0)
        day = int(body.get("day") or 0)
        try:
            from seasons import SeasonType

            season = SeasonType(season)
        except Exception:
            pass
        svc.add_a_holiday(data, season, day)
    except Exception:
        return


@MessageHandler(KIND_REMOVE_HOLIDAY)
def _host_remove_holiday(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    holiday_id = int(body.get("holiday_id") or 0)
    if not holiday_id:
        return
    try:
        import services

        svc = services.holiday_service()
        if svc is None:
            return
        svc.remove_a_holiday(holiday_id)
    except Exception:
        return