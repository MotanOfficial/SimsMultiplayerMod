"""Retail / business command relays (open, markup, ads, quality, funds, hire/fire).

Joiners never mutate BusinessManager locally; they relay intent to the host.
"""

from __future__ import division

from simmp.deep import (
    KIND_FIRE_BUSINESS_EMPLOYEE,
    KIND_HIRE_BUSINESS_EMPLOYEE,
    KIND_SET_BUSINESS_ADVERTISING,
    KIND_SET_BUSINESS_MARKUP,
    KIND_SET_BUSINESS_OPEN,
    KIND_SET_BUSINESS_QUALITY,
    KIND_TRANSFER_RETAIL_FUNDS,
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


def _business_manager(zone_id=None):
    try:
        import services

        svc = services.business_service()
        if zone_id:
            return svc.get_business_manager_for_zone(zone_id=int(zone_id))
        return svc.get_business_manager_for_zone()
    except Exception:
        return None


def install_business_hooks():
    ok = False

    try:
        from business import business_commands
    except Exception:
        business_commands = None

    if business_commands is not None:
        set_open_fn = getattr(business_commands, "set_open", None)
        if set_open_fn is not None:

            @Override(set_open_fn, role=Role.JOINER)
            def _set_open_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    is_open = _as_bool_flag(args[0]) if args else False
                    zone_id = int(args[1]) if len(args) > 1 and args[1] is not None else 0
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_SET_BUSINESS_OPEN,
                    {
                        "is_open": is_open,
                        "zone_id": zone_id,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        markup_fn = getattr(business_commands, "set_markup_multiplier", None)
        if markup_fn is None:
            markup_fn = getattr(business_commands, "set_markup", None)
        if markup_fn is not None:

            @Override(markup_fn, role=Role.JOINER)
            def _set_markup_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    markup = float(args[0]) if args else 0.0
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_SET_BUSINESS_MARKUP,
                    {
                        "markup_multiplier": markup,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        ads_fn = getattr(business_commands, "set_advertising_type", None)
        if ads_fn is None:
            ads_fn = getattr(business_commands, "set_advertising", None)
        if ads_fn is not None:

            @Override(ads_fn, role=Role.JOINER)
            def _set_advertising_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    ads = float(args[0]) if args else 0.0
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_SET_BUSINESS_ADVERTISING,
                    {
                        "advertising_type": ads,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        quality_fn = getattr(business_commands, "set_quality", None)
        if quality_fn is not None:

            @Override(quality_fn, role=Role.JOINER)
            def _set_quality_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    quality = int(getattr(args[0], "value", args[0])) if args else 0
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_SET_BUSINESS_QUALITY,
                    {
                        "quality": quality,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        hire_fn = getattr(business_commands, "hire_business_employee", None)
        if hire_fn is None:
            hire_fn = getattr(business_commands, "employee_hire", None)
        if hire_fn is not None:

            @Override(hire_fn, role=Role.JOINER)
            def _hire_employee_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    sim_id = _sim_id_from_arg(args[0] if args else None)
                    emp_type = int(getattr(args[1], "value", args[1])) if len(args) > 1 else 0
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_HIRE_BUSINESS_EMPLOYEE,
                    {
                        "sim_id": sim_id,
                        "employee_type": emp_type,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        fire_fn = getattr(business_commands, "fire_business_employee", None)
        if fire_fn is None:
            fire_fn = getattr(business_commands, "employee_fire", None)
        if fire_fn is not None:

            @Override(fire_fn, role=Role.JOINER)
            def _fire_employee_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    sim_id = _sim_id_from_arg(args[0] if args else None)
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_FIRE_BUSINESS_EMPLOYEE,
                    {
                        "sim_id": sim_id,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

    try:
        from retail import retail_commands
    except Exception:
        retail_commands = None

    if retail_commands is not None:
        xfer_fn = getattr(retail_commands, "transfer_retail_funds", None)
        if xfer_fn is None:
            xfer_fn = getattr(retail_commands, "transfer_funds", None)
        if xfer_fn is not None:

            @Override(xfer_fn, role=Role.JOINER)
            def _transfer_retail_funds_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    amount = int(args[0]) if args else 0
                    from_zone = int(args[1]) if len(args) > 1 else 0
                    to_zone = int(args[2]) if len(args) > 2 else 0
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_TRANSFER_RETAIL_FUNDS,
                    {
                        "amount": amount,
                        "from_zone_id": from_zone,
                        "to_zone_id": to_zone,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

    return ok


def _run_employee_interaction(affordance, target_sim, player_id):
    if affordance is None or target_sim is None:
        return
    try:
        from interactions.context import InteractionContext
        from interactions.priority import Priority
        from simmp_client.deep import sim_select
        import services

        actor_id = sim_select.get_active_sim_id_for_player(player_id)
        actor_info = services.sim_info_manager().get(actor_id) if actor_id else None
        actor = actor_info.get_sim_instance() if actor_info is not None else None
        if actor is None:
            actor = services.get_active_sim()
        if actor is None:
            return
        ctx = InteractionContext(actor, InteractionContext.SOURCE_PIE_MENU, Priority.High)
        actor.push_super_affordance(
            affordance, None, ctx, picked_item_ids=(int(target_sim.sim_info.id),)
        )
    except TypeError:
        try:
            from interactions.context import InteractionContext
            from interactions.priority import Priority
            import services

            actor = services.get_active_sim()
            if actor is None:
                return
            ctx = InteractionContext(actor, InteractionContext.SOURCE_PIE_MENU, Priority.High)
            actor.push_super_affordance(affordance, target_sim, ctx)
        except Exception:
            return
    except Exception:
        return


@MessageHandler(KIND_SET_BUSINESS_OPEN)
def _host_set_business_open(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    zone_id = int(body.get("zone_id") or 0)
    mgr = _business_manager(zone_id or None)
    if mgr is None:
        return
    try:
        mgr.set_open(bool(body.get("is_open")))
    except Exception:
        return


@MessageHandler(KIND_SET_BUSINESS_MARKUP)
def _host_set_business_markup(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    mgr = _business_manager()
    if mgr is None:
        return
    try:
        mgr.set_markup_multiplier(float(body.get("markup_multiplier") or 0.0))
    except Exception:
        return


@MessageHandler(KIND_SET_BUSINESS_ADVERTISING)
def _host_set_business_advertising(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    mgr = _business_manager()
    if mgr is None:
        return
    try:
        from business.business_enums import BusinessAdvertisingType

        ads = BusinessAdvertisingType(int(float(body.get("advertising_type") or 0.0)))
        mgr.set_advertising_type(ads)
    except Exception:
        try:
            mgr.set_advertising_type(int(float(body.get("advertising_type") or 0.0)))
        except Exception:
            return


@MessageHandler(KIND_SET_BUSINESS_QUALITY)
def _host_set_business_quality(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    mgr = _business_manager()
    if mgr is None:
        return
    try:
        from business.business_enums import BusinessQualityType

        quality = BusinessQualityType(int(body.get("quality") or 0))
        mgr.set_quality(quality)
    except Exception:
        try:
            mgr.set_quality(int(body.get("quality") or 0))
        except Exception:
            return


@MessageHandler(KIND_TRANSFER_RETAIL_FUNDS)
def _host_transfer_retail_funds(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    amount = int(body.get("amount") or 0)
    if amount < 1:
        return
    from_zone = int(body.get("from_zone_id") or 0)
    to_zone = int(body.get("to_zone_id") or 0)
    try:
        import services
        from sims.funds import transfer_funds

        from_mgr = services.business_service().get_business_manager_for_zone(zone_id=from_zone) if from_zone else None
        to_mgr = services.business_service().get_business_manager_for_zone(zone_id=to_zone) if to_zone else None
        if from_mgr is None and to_mgr is None:
            return
        if from_mgr is None:
            hh = services.household_manager().get(to_mgr.owner_household_id)
            transfer_funds(amount, from_funds=hh.funds, to_funds=to_mgr.funds)
        elif to_mgr is None:
            hh = services.household_manager().get(from_mgr.owner_household_id)
            transfer_funds(amount, from_funds=from_mgr.funds, to_funds=hh.funds)
        else:
            transfer_funds(amount, from_funds=from_mgr.funds, to_funds=to_mgr.funds)
        if from_mgr is not None:
            try:
                from_mgr.send_business_funds_update()
            except Exception:
                pass
        if to_mgr is not None:
            try:
                to_mgr.send_business_funds_update()
            except Exception:
                pass
    except Exception:
        return


@MessageHandler(KIND_HIRE_BUSINESS_EMPLOYEE)
def _host_hire_business_employee(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    emp_type = int(body.get("employee_type") or 0)
    player_id = int(body.get("player_id") or 0)
    if not sim_id:
        return
    try:
        import services
        from business.business_enums import BusinessEmployeeType

        mgr = _business_manager()
        if mgr is None:
            return
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        sim = sim_info.get_sim_instance()
        if sim is None:
            return
        try:
            typed = BusinessEmployeeType(emp_type)
        except Exception:
            typed = emp_type
        tuning = mgr._employee_manager.get_employee_tuning_data_for_employee_type(typed)
        if tuning is None:
            return
        _run_employee_interaction(tuning.interaction_hire, sim, player_id)
    except Exception:
        return


@MessageHandler(KIND_FIRE_BUSINESS_EMPLOYEE)
def _host_fire_business_employee(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    player_id = int(body.get("player_id") or 0)
    if not sim_id:
        return
    try:
        import services

        mgr = _business_manager()
        if mgr is None:
            return
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        sim = sim_info.get_sim_instance()
        if sim is None:
            return
        emp_mgr = mgr._employee_manager
        data = emp_mgr.get_employee_data(sim_info)
        if data is None:
            return
        tuning = emp_mgr.get_employee_tuning_data_for_employee_type(data.employee_type)
        if tuning is None:
            return
        _run_employee_interaction(tuning.interaction_fire, sim, player_id)
    except Exception:
        return