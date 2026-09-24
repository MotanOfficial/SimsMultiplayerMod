"""Bills utility relays (sell excess / end-of-bill action).

Joiners relay utility bill UI intent; host mutates active household bills_manager.
"""

from __future__ import division

from simmp.deep import (
    KIND_SELL_EXCESS_UTILITY,
    KIND_SET_UTILITY_END_BILL_ACTION,
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
        return int(getattr(value, "value", value))
    except Exception:
        return default


def _bills_manager():
    try:
        import services

        household = services.active_household()
        if household is None:
            return None
        return getattr(household, "bills_manager", None)
    except Exception:
        return None


def install_bills_hooks():
    try:
        from sims import bills_commands
    except Exception:
        try:
            import bills_commands
        except Exception:
            return False

    ok = False

    sell_fn = getattr(bills_commands, "sell_excess_utility", None)
    if sell_fn is not None:

        @Override(sell_fn, role=Role.JOINER)
        def _sell_excess_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                utility = _as_int(args[0] if args else kwargs.get("utility"))
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SELL_EXCESS_UTILITY,
                {
                    "utility": utility,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    action_fn = getattr(bills_commands, "set_utility_end_bill_action", None)
    if action_fn is not None:

        @Override(action_fn, role=Role.JOINER)
        def _set_end_action_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                utility = _as_int(args[0] if args else kwargs.get("utility"))
                utility_action = _as_int(
                    args[1] if len(args) > 1 else kwargs.get("utility_action")
                )
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SET_UTILITY_END_BILL_ACTION,
                {
                    "utility": utility,
                    "utility_action": utility_action,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


@MessageHandler(KIND_SELL_EXCESS_UTILITY)
def _host_sell_excess_utility(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    mgr = _bills_manager()
    if mgr is None:
        return
    try:
        utility = int(body.get("utility") or 0)
        try:
            from sims.household_utilities.utility_types import Utilities

            utility = Utilities(utility)
        except Exception:
            pass
        mgr.sell_excess_utility(utility)
    except Exception:
        return


@MessageHandler(KIND_SET_UTILITY_END_BILL_ACTION)
def _host_set_utility_end_bill_action(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    mgr = _bills_manager()
    if mgr is None:
        return
    try:
        utility = int(body.get("utility") or 0)
        action = int(body.get("utility_action") or 0)
        try:
            from sims.household_utilities.utility_types import Utilities

            utility = Utilities(utility)
        except Exception:
            pass
        try:
            from sims.bills_enums import UtilityEndOfBillAction

            action = UtilityEndOfBillAction(action)
        except Exception:
            pass
        mgr.set_utility_end_bill_action(utility, action)
    except Exception:
        return
