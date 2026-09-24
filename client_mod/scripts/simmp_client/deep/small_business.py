"""Small-business (EP) command relays: register/update/open + configurator UI.

Opaque ``business_data`` is EA SetBusinessData text-format from the joiner UI.
"""

from __future__ import division

from simmp.deep import (
    KIND_PUSH_REGISTER_BUSINESS,
    KIND_REGISTER_SMALL_BUSINESS,
    KIND_SET_OPEN_SMALL_BUSINESS,
    KIND_SHOW_SMALL_BUSINESS_CONFIGURATOR,
    KIND_SHOW_SMALL_BUSINESS_EMPLOYEE_MGMT,
    KIND_UPDATE_SMALL_BUSINESS,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION


def _as_bool_flag(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value) in ("1", "True", "true")


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


def _player_sim_info(player_id):
    try:
        from simmp_client.deep import sim_select
        import services

        sim_id = sim_select.get_active_sim_id_for_player(player_id)
        if not sim_id:
            return None
        return services.sim_info_manager().get(sim_id)
    except Exception:
        return None


def install_small_business_hooks():
    try:
        from business import business_commands
    except Exception:
        return False

    ok = False

    push_fn = getattr(business_commands, "push_active_sim_to_register_business", None)
    if push_fn is not None:

        @Override(push_fn, role=Role.JOINER)
        def _push_register_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                business_type = int(getattr(args[0], "value", args[0])) if args else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_PUSH_REGISTER_BUSINESS,
                {
                    "business_type": business_type,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    cfg_fn = getattr(business_commands, "request_show_small_business_configurator", None)
    if cfg_fn is not None:

        @Override(cfg_fn, role=Role.JOINER)
        def _show_configurator_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                is_edit = _as_bool_flag(args[0]) if args else False
                opt_sim = args[1] if len(args) > 1 else None
                sim_id = _sim_id_from_arg(opt_sim)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SHOW_SMALL_BUSINESS_CONFIGURATOR,
                {
                    "is_edit": is_edit,
                    "player_id": int(SESSION.player_id or 0),
                    "sim_id": sim_id,
                },
            )
            return None

        ok = True

    reg_fn = getattr(business_commands, "register_small_business", None)
    if reg_fn is not None:

        @Override(reg_fn, role=Role.JOINER)
        def _register_small_business_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                opt_sim = args[0] if args else None
                business_data = args[1] if len(args) > 1 else kwargs.get("business_data")
                sim_id = _sim_id_from_arg(opt_sim)
                data_s = str(business_data) if business_data is not None else ""
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_REGISTER_SMALL_BUSINESS,
                {
                    "sim_id": sim_id,
                    "business_data": data_s,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return True

        ok = True

    upd_fn = getattr(business_commands, "update_small_business", None)
    if upd_fn is not None:

        @Override(upd_fn, role=Role.JOINER)
        def _update_small_business_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                opt_sim = args[0] if args else None
                business_data = args[1] if len(args) > 1 else kwargs.get("business_data")
                sim_id = _sim_id_from_arg(opt_sim)
                data_s = str(business_data) if business_data is not None else ""
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_UPDATE_SMALL_BUSINESS,
                {
                    "sim_id": sim_id,
                    "business_data": data_s,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    open_fn = getattr(business_commands, "set_open_small_business", None)
    if open_fn is not None:

        @Override(open_fn, role=Role.JOINER)
        def _set_open_small_business_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                is_open = _as_bool_flag(args[0]) if args else False
                opt_sim = args[1] if len(args) > 1 else None
                sim_id = _sim_id_from_arg(opt_sim)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SET_OPEN_SMALL_BUSINESS,
                {
                    "is_open": is_open,
                    "sim_id": sim_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    emp_fn = getattr(business_commands, "show_small_business_employee_management_dialog", None)
    if emp_fn is not None:

        @Override(emp_fn, role=Role.JOINER)
        def _show_employee_mgmt_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                opt_sim = args[0] if args else None
                sim_id = _sim_id_from_arg(opt_sim)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SHOW_SMALL_BUSINESS_EMPLOYEE_MGMT,
                {
                    "sim_id": sim_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


def _parse_business_data(data_s):
    try:
        from google.protobuf import text_format
        from protocolbuffers import Business_pb2

        msg = Business_pb2.SetBusinessData()
        if data_s:
            text_format.Merge(data_s, msg)
        return msg
    except Exception:
        return None


@MessageHandler(KIND_PUSH_REGISTER_BUSINESS)
def _host_push_register_business(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    business_type = int(body.get("business_type") or 0)
    try:
        import services
        from business.business_enums import BusinessType
        from interactions.context import InteractionContext
        from interactions.priority import Priority
        from simmp_client.deep import sim_select

        sim = sim_select.get_active_sim_for_player(player_id)
        if sim is None:
            return
        try:
            btype = BusinessType(business_type)
        except Exception:
            btype = business_type
        tuning = services.business_service().get_business_tuning_data_for_business_type(btype)
        if tuning is None:
            return
        ctx = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
        sim.push_super_affordance(tuning.register_business_affordance, sim, ctx)
    except Exception:
        return


@MessageHandler(KIND_SHOW_SMALL_BUSINESS_CONFIGURATOR)
def _host_show_small_business_configurator(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from business import business_commands

        is_edit = bool(body.get("is_edit"))
        sim_id = int(body.get("sim_id") or 0)
        if sim_id:
            business_commands.request_show_small_business_configurator(is_edit, sim_id)
        else:
            business_commands.request_show_small_business_configurator(is_edit)
    except Exception:
        return


@MessageHandler(KIND_REGISTER_SMALL_BUSINESS)
def _host_register_small_business(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    if not sim_id:
        return
    try:
        import services
        from business.business_enums import BusinessType

        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None or sim_info.household is None:
            return
        data = _parse_business_data(body.get("business_data") or "")
        if data is None:
            return
        if not getattr(data, "sim_id", 0):
            try:
                data.sim_id = sim_info.id
            except Exception:
                pass
        services.business_service().make_owner(
            sim_info.household.id,
            BusinessType.SMALL_BUSINESS,
            None,
            business_data=data,
        )
        services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
    except Exception:
        return


@MessageHandler(KIND_UPDATE_SMALL_BUSINESS)
def _host_update_small_business(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    data_s = body.get("business_data") or ""
    if not sim_id or not data_s:
        return
    try:
        import services

        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        data = _parse_business_data(data_s)
        if data is None:
            return
        mgr = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
        if mgr is None:
            return
        mgr.update_small_business_from_ui(data)
        try:
            mgr.send_data_to_client()
        except Exception:
            pass
    except Exception:
        return


@MessageHandler(KIND_SET_OPEN_SMALL_BUSINESS)
def _host_set_open_small_business(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    is_open = bool(body.get("is_open"))
    if not sim_id:
        return
    try:
        import services
        from business.business_enums import BusinessType

        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        if is_open:
            mgr = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
        else:
            mgr = services.business_service().get_business_manager_for_zone(services.current_zone_id())
            if mgr is not None and getattr(mgr, "owner_sim_id", None) != sim_info.id:
                mgr = None
        if mgr is None:
            return
        if getattr(mgr, "business_type", None) != BusinessType.SMALL_BUSINESS:
            # Some builds compare by int value.
            if int(getattr(mgr, "business_type", -1)) != int(getattr(BusinessType, "SMALL_BUSINESS", -2)):
                return
        mgr.set_open(is_open)
    except Exception:
        return


@MessageHandler(KIND_SHOW_SMALL_BUSINESS_EMPLOYEE_MGMT)
def _host_show_small_business_employee_mgmt(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    try:
        from business import business_commands

        if sim_id:
            business_commands.show_small_business_employee_management_dialog(sim_id)
        else:
            business_commands.show_small_business_employee_management_dialog()
    except Exception:
        return