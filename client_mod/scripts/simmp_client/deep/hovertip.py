"""UI create-hovertip relay."""

from __future__ import division

from simmp.deep import KIND_UI_CREATE_HOVERTIP, WrapperMessage
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
    text = str(value).strip().lower()
    return text in ("1", "true", "yes", "on")


def install_hovertip_hooks():
    try:
        from server_commands import ui_commands
    except Exception:
        return False

    fn = getattr(ui_commands, "ui_create_hovertip", None)
    if fn is None:
        return False

    @Override(fn, role=Role.JOINER)
    def _hovertip_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            target_id = args[0] if args else kwargs.get("target_id")
            if target_id is None:
                return None
            target_id = _as_int(target_id)
            is_from_ui = _as_bool(args[1] if len(args) > 1 else kwargs.get("is_from_ui", False))
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_UI_CREATE_HOVERTIP,
            {
                "target_id": target_id,
                "is_from_ui": is_from_ui,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        return None

    return True


@MessageHandler(KIND_UI_CREATE_HOVERTIP)
def _host_ui_create_hovertip(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services
        from protocolbuffers.UI_pb2 import HovertipCreated
        from protocolbuffers.DistributorOps_pb2 import Operation
        from distributor.ops import GenericProtocolBufferOp
        from distributor.system import Distributor

        zone = services.current_zone()
        if zone is None:
            return
        obj = zone.find_object(int(body.get("target_id") or 0))
        if obj is None or not getattr(obj, "valid_for_distribution", False):
            return
        success = bool(obj.on_hovertip_requested())
        msg = HovertipCreated()
        msg.is_from_ui = bool(body.get("is_from_ui"))
        msg.is_success = success
        op = GenericProtocolBufferOp(Operation.HOVERTIP_CREATED, msg)
        Distributor.instance().add_op(obj, op)
    except Exception:
        return
