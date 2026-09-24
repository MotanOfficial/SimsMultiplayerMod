"""Dynasty (Bloodlines) configurator + create/update/remove relays.

Opaque ``dynasty_data`` strings are EA SetDynastyData text-format payloads
from the joiner UI; the host merges them and mutates dynasty_service.
Show-configurator replays original for Distributor UI fan-out.
"""

from __future__ import division

from simmp.deep import (
    KIND_CREATE_DYNASTY,
    KIND_REMOVE_DYNASTY,
    KIND_REQUEST_SHOW_DYNASTY_CONFIGURATOR,
    KIND_UPDATE_DYNASTY,
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
        return int(getattr(value, "id", getattr(value, "value", value)))
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


def _dynasty_service():
    try:
        import services

        return services.dynasty_service()
    except Exception:
        return None


def _parse_dynasty_pb(data_s):
    try:
        from google.protobuf import text_format
        from protocolbuffers import GameplaySaveData_pb2

        data = GameplaySaveData_pb2.SetDynastyData()
        text_format.Merge(data_s or "", data)
        return data
    except Exception:
        return None


def install_dynasty_hooks():
    try:
        from dynasty import dynasty_commands
    except Exception:
        return False

    ok = False

    show_fn = getattr(dynasty_commands, "request_show_dynasty_configurator", None)
    if show_fn is not None:

        @Override(show_fn, role=Role.JOINER)
        def _show_configurator_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                sim_id = _as_int(args[0] if args else kwargs.get("sim_id"))
                dynasty_id = _as_int(
                    args[1] if len(args) > 1 else kwargs.get("dynasty_id")
                )
                view_mine = _as_bool(
                    args[2] if len(args) > 2 else kwargs.get("view_my_dynasty_mode", False)
                )
                from_marriage = _as_bool(
                    args[3] if len(args) > 3 else kwargs.get("from_marriage", False)
                )
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_REQUEST_SHOW_DYNASTY_CONFIGURATOR,
                {
                    "sim_id": sim_id,
                    "dynasty_id": dynasty_id,
                    "view_my_dynasty_mode": view_mine,
                    "from_marriage": from_marriage,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    create_fn = getattr(dynasty_commands, "create_dynasty", None)
    if create_fn is not None:

        @Override(create_fn, role=Role.JOINER)
        def _create_dynasty_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                dynasty_data = args[0] if args else kwargs.get("dynasty_data")
                data_s = str(dynasty_data) if dynasty_data is not None else ""
                from_existing = _as_bool(
                    args[1] if len(args) > 1 else kwargs.get("from_existing_dynasty", False)
                )
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_CREATE_DYNASTY,
                {
                    "dynasty_data": data_s,
                    "from_existing_dynasty": from_existing,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    update_fn = getattr(dynasty_commands, "update_dynasty", None)
    if update_fn is not None:

        @Override(update_fn, role=Role.JOINER)
        def _update_dynasty_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                dynasty_data = args[0] if args else kwargs.get("dynasty_data")
                data_s = str(dynasty_data) if dynasty_data is not None else ""
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_UPDATE_DYNASTY,
                {
                    "dynasty_data": data_s,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    remove_fn = getattr(dynasty_commands, "remove_dynasty", None)
    if remove_fn is not None:

        @Override(remove_fn, role=Role.JOINER)
        def _remove_dynasty_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                dynasty_id = _as_int(args[0] if args else kwargs.get("dynasty_id"))
            except Exception:
                return original(*args, **kwargs)
            if not dynasty_id:
                return False
            _relay_to_host(
                KIND_REMOVE_DYNASTY,
                {
                    "dynasty_id": dynasty_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return True

        ok = True

    return ok


@MessageHandler(KIND_REQUEST_SHOW_DYNASTY_CONFIGURATOR)
def _host_request_show_dynasty_configurator(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from dynasty import dynasty_commands

        dynasty_commands.request_show_dynasty_configurator(
            int(body.get("sim_id") or 0),
            int(body.get("dynasty_id") or 0),
            bool(body.get("view_my_dynasty_mode")),
            bool(body.get("from_marriage")),
        )
    except Exception:
        return


@MessageHandler(KIND_CREATE_DYNASTY)
def _host_create_dynasty(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    data = _parse_dynasty_pb(body.get("dynasty_data") or "")
    if data is None:
        return
    svc = _dynasty_service()
    if svc is None:
        return
    try:
        svc.add_dynasty(
            dynasty_data=data,
            from_existing_dynasty=bool(body.get("from_existing_dynasty")),
        )
    except Exception:
        try:
            svc.add_dynasty(data, bool(body.get("from_existing_dynasty")))
        except Exception:
            return


@MessageHandler(KIND_UPDATE_DYNASTY)
def _host_update_dynasty(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    data = _parse_dynasty_pb(body.get("dynasty_data") or "")
    if data is None:
        return
    svc = _dynasty_service()
    if svc is None:
        return
    try:
        dynasty = svc.get_dynasty(getattr(data, "dynasty_id", 0))
        if dynasty is None:
            return
        dynasty.update_from_data(dynasty_data=data)
    except Exception:
        try:
            dynasty = svc.get_dynasty(data.dynasty_id)
            if dynasty is None:
                return
            dynasty.update_from_data(data)
        except Exception:
            return


@MessageHandler(KIND_REMOVE_DYNASTY)
def _host_remove_dynasty(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    dynasty_id = int(body.get("dynasty_id") or 0)
    if not dynasty_id:
        return
    svc = _dynasty_service()
    if svc is None:
        return
    try:
        dynasty = svc.get_dynasty(dynasty_id)
        if dynasty is not None:
            svc.remove_dynasty(dynasty)
    except Exception:
        return
