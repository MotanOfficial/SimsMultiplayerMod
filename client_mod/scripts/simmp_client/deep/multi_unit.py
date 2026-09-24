"""Multi-unit (For Rent) rental management relays.

Joiners relay landlord/tenant UI intent; host owns rental business_manager
mutations. Show-management replays original for Distributor UI fan-out.
"""

from __future__ import division

from simmp.deep import (
    KIND_NOTIFY_BUSINESS_RULES_STATE_CHANGE,
    KIND_SELECT_TENANT,
    KIND_SET_UNIT_RENT_PRICE,
    KIND_SET_UNIT_SIGNED_LEASE_LENGTH,
    KIND_SHOW_RENTAL_UNIT_MANAGEMENT,
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


def _encode_rule_list(rule_list):
    if rule_list is None:
        return ""
    if isinstance(rule_list, str):
        return rule_list
    parts = []
    try:
        for item in rule_list:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                rid = _as_int(item[0])
                state = _as_int(item[1])
                parts.append("%s:%s" % (rid, state))
            else:
                parts.append(str(item))
    except Exception:
        return str(rule_list)
    return ",".join(parts)


def _decode_rule_list(data):
    out = []
    if not data:
        return out
    for part in str(data).split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        left, right = part.split(":", 1)
        try:
            out.append((int(left), int(right)))
        except Exception:
            continue
    return out


def _rental_manager(zone_id):
    try:
        import services
        from business.business_enums import BusinessType

        mgr = services.business_service().get_business_manager_for_zone(zone_id)
        if mgr is None:
            return None
        if getattr(mgr, "business_type", None) != BusinessType.RENTAL_UNIT:
            return None
        return mgr
    except Exception:
        return None


def install_multi_unit_hooks():
    ok = False

    try:
        from multi_unit import multi_unit_commands
    except Exception:
        multi_unit_commands = None

    if multi_unit_commands is not None:
        show_fn = getattr(multi_unit_commands, "show_rental_unit_management", None)
        if show_fn is not None:

            @Override(show_fn, role=Role.JOINER)
            def _show_rental_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    zone_id = _as_int(args[0] if args else kwargs.get("zone_id"), -1)
                    house_desc = _as_int(
                        args[1] if len(args) > 1 else kwargs.get("house_description_id"),
                        -1,
                    )
                    is_app = _as_bool(
                        args[2] if len(args) > 2 else kwargs.get("is_application_process", False)
                    )
                    opt_sim = _as_int(
                        args[3] if len(args) > 3 else kwargs.get("opt_sim"),
                        -1,
                    )
                    tenant_view = _as_bool(
                        args[4] if len(args) > 4 else kwargs.get("tenant_view_override", False)
                    )
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_SHOW_RENTAL_UNIT_MANAGEMENT,
                    {
                        "zone_id": zone_id,
                        "house_description_id": house_desc,
                        "is_application_process": is_app,
                        "opt_sim": opt_sim,
                        "tenant_view_override": tenant_view,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return True

            ok = True

        rent_fn = getattr(multi_unit_commands, "set_unit_rent_price", None)
        if rent_fn is not None:

            @Override(rent_fn, role=Role.JOINER)
            def _set_rent_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    zone_id = _as_int(args[0] if args else kwargs.get("zone_id"))
                    rent_price = _as_int(args[1] if len(args) > 1 else kwargs.get("rent_price"))
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_SET_UNIT_RENT_PRICE,
                    {
                        "zone_id": zone_id,
                        "rent_price": rent_price,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return True

            ok = True

        lease_fn = getattr(multi_unit_commands, "set_unit_signed_lease_length", None)
        if lease_fn is not None:

            @Override(lease_fn, role=Role.JOINER)
            def _set_lease_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    zone_id = _as_int(args[0] if args else kwargs.get("zone_id"))
                    length = _as_int(args[1] if len(args) > 1 else kwargs.get("length"))
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_SET_UNIT_SIGNED_LEASE_LENGTH,
                    {
                        "zone_id": zone_id,
                        "length": length,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return True

            ok = True

        select_fn = getattr(multi_unit_commands, "select_tenant", None)
        if select_fn is not None:

            @Override(select_fn, role=Role.JOINER)
            def _select_tenant_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    household_id = _as_int(args[0] if args else kwargs.get("household_id"))
                    zone_id = _as_int(args[1] if len(args) > 1 else kwargs.get("zone_id"))
                    name = args[2] if len(args) > 2 else kwargs.get("household_name", "")
                    name_s = str(name) if name is not None else ""
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_SELECT_TENANT,
                    {
                        "household_id": household_id,
                        "zone_id": zone_id,
                        "household_name": name_s,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

    try:
        import areaserver

        notify_fn = getattr(areaserver, "c_api_notify_business_rules_state_change", None)
    except Exception:
        notify_fn = None

    if notify_fn is not None:

        @Override(notify_fn, role=Role.JOINER)
        def _notify_rules_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                zone_id = _as_int(args[0] if args else kwargs.get("zone_id"))
                rule_list = args[1] if len(args) > 1 else kwargs.get("rule_list")
                rule_s = _encode_rule_list(rule_list)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_NOTIFY_BUSINESS_RULES_STATE_CHANGE,
                {
                    "zone_id": zone_id,
                    "rule_list": rule_s,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


@MessageHandler(KIND_SHOW_RENTAL_UNIT_MANAGEMENT)
def _host_show_rental_unit_management(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from multi_unit import multi_unit_commands

        zone_id = int(body.get("zone_id") or 0)
        house_desc = int(body.get("house_description_id") if body.get("house_description_id") is not None else -1)
        is_app = bool(body.get("is_application_process"))
        opt_sim = int(body.get("opt_sim") if body.get("opt_sim") is not None else -1)
        tenant_view = bool(body.get("tenant_view_override"))
        # Replay original so SHOW_RENTAL_UNIT_MANAGEMENT fans via GameNetwork.
        if house_desc < 0 and opt_sim < 0:
            multi_unit_commands.show_rental_unit_management(
                zone_id, None, is_app, None, tenant_view
            )
        else:
            multi_unit_commands.show_rental_unit_management(
                zone_id,
                None if house_desc < 0 else house_desc,
                is_app,
                None if opt_sim < 0 else opt_sim,
                tenant_view,
            )
    except Exception:
        return


@MessageHandler(KIND_NOTIFY_BUSINESS_RULES_STATE_CHANGE)
def _host_notify_business_rules(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    zone_id = int(body.get("zone_id") or 0)
    rules = _decode_rule_list(body.get("rule_list") or "")
    try:
        import services
        from business.business_rule_enums import BusinessRuleState

        mgr = services.business_service().get_business_manager_for_zone(zone_id)
        if mgr is None or not getattr(mgr, "has_rules", False):
            return
        try:
            mgr.reset_rules(default_state=BusinessRuleState.DISABLED)
        except Exception:
            mgr.reset_rules(BusinessRuleState.DISABLED)
        for rule_id, state in rules:
            try:
                state_enum = BusinessRuleState(state)
            except Exception:
                state_enum = state
            try:
                mgr.set_rule_state(rule_id, state_enum, override_rule_cooldown_time=0)
            except Exception:
                try:
                    mgr.set_rule_state(rule_id, state_enum, 0)
                except Exception:
                    continue
    except Exception:
        return


@MessageHandler(KIND_SET_UNIT_RENT_PRICE)
def _host_set_unit_rent_price(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    mgr = _rental_manager(int(body.get("zone_id") or 0))
    if mgr is None:
        return
    try:
        mgr.set_rent(int(body.get("rent_price") or 0))
    except Exception:
        return


@MessageHandler(KIND_SET_UNIT_SIGNED_LEASE_LENGTH)
def _host_set_unit_signed_lease_length(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    mgr = _rental_manager(int(body.get("zone_id") or 0))
    if mgr is None:
        return
    try:
        mgr.signed_lease_length = int(body.get("length") or 0)
    except Exception:
        return


@MessageHandler(KIND_SELECT_TENANT)
def _host_select_tenant(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services

        svc = services.get_tenant_application_service()
        if svc is None:
            return
        svc.move_in_household(
            int(body.get("household_id") or 0),
            int(body.get("zone_id") or 0),
            body.get("household_name") or "",
        )
    except Exception:
        return
