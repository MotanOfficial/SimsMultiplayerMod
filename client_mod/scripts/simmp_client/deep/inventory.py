"""Inventory sell/purchase/view + household funds deep relays.

Joiners never mutate household money or inventory stacks locally; they relay
intent to the host. Host applies funds via HouseholdFunds and runs inventory
commands against the live Situation/object graph. UI updates fan out through
Client.send_message -> GameNetworkMessage (already patched in game_network).
"""

from __future__ import division

import json

from simmp.deep import (
    KIND_INVENTORY_SELL_MULTIPLE,
    KIND_INVENTORY_VIEW_UPDATE,
    KIND_MODIFY_HOUSEHOLD_FUNDS,
    KIND_PURCHASE_PICKER_RESPONSE,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION

# Suppress re-entrant funds apply when host MessageHandler calls into game APIs.
_applying_funds = False


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


def install_inventory_hooks():
    ok = False

    # --- Funds: joiner build-buy / purchase money changes ---
    try:
        import build_buy

        funds_fn = getattr(build_buy, "c_api_modify_household_funds", None)
    except Exception:
        funds_fn = None

    if funds_fn is not None:

        @Override(funds_fn, role=Role.JOINER)
        def _modify_household_funds_joiner(original, amount, household_id, reason, zone_id, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host or _applying_funds:
                return original(amount, household_id, reason, zone_id, *args, **kwargs)
            try:
                amount_i = int(amount)
                household_i = int(household_id)
                reason_i = int(getattr(reason, "value", reason) or 0)
                zone_i = int(zone_id)
            except Exception:
                return original(amount, household_id, reason, zone_id, *args, **kwargs)
            _relay_to_host(
                KIND_MODIFY_HOUSEHOLD_FUNDS,
                {
                    "amount": amount_i,
                    "household_id": household_i,
                    "reason": reason_i,
                    "zone_id": zone_i,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            # Host owns money; suppress local joiner mutation.
            return True

        ok = True

    try:
        from server_commands import inventory_commands
    except Exception:
        return ok

    sell_fn = getattr(inventory_commands, "sim_inventory_sell_multiple", None)
    if sell_fn is not None:

        @Override(sell_fn, role=Role.JOINER)
        def _sim_inventory_sell_multiple_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                msg = args[0] if args else kwargs.get("msg")
                msg_s = str(msg) if msg is not None else ""
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_INVENTORY_SELL_MULTIPLE,
                {
                    "msg": msg_s,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    purchase_fn = getattr(inventory_commands, "purchase_picker_response_by_ids", None)
    if purchase_fn is not None:

        @Override(purchase_fn, role=Role.JOINER)
        def _purchase_picker_response_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                inventory_target = args[0] if args else 0
                inventory_source = args[1] if len(args) > 1 else 0
                currency_type = int(args[2]) if len(args) > 2 else 0
                dialog_id = int(args[3]) if len(args) > 3 else 0
                delivery_method = int(args[4]) if len(args) > 4 else 0
                object_ids_flag = _as_bool_flag(args[5]) if len(args) > 5 else False
                tail = list(args[6:]) if len(args) > 6 else []
                target_i = int(getattr(inventory_target, "target_id", inventory_target) or 0)
                source_i = int(getattr(inventory_source, "target_id", inventory_source) or 0)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_PURCHASE_PICKER_RESPONSE,
                {
                    "inventory_target": target_i,
                    "inventory_source": source_i,
                    "currency_type": currency_type,
                    "dialog_id": dialog_id,
                    "delivery_method": delivery_method,
                    "object_ids_or_definition_ids": object_ids_flag,
                    "ids_json": json.dumps([str(x) for x in tail]),
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    view_fn = getattr(inventory_commands, "inventory_view_update", None)
    if view_fn is None:
        view_fn = getattr(inventory_commands, "view_update", None)
    if view_fn is not None:

        @Override(view_fn, role=Role.JOINER)
        def _inventory_view_update_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                obj_id = int(args[0]) if args else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_INVENTORY_VIEW_UPDATE,
                {
                    "obj_id": obj_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return True

        ok = True

    return ok


def _apply_household_funds(amount, household_id, reason):
    """Host-side money mutate. Prefers business manager, then household funds."""
    global _applying_funds
    _applying_funds = True
    try:
        import services

        try:
            biz = services.business_service().get_business_manager_for_zone()
            if biz is not None:
                biz.modify_funds(int(amount), from_item_sold=False)
                return True
        except Exception:
            pass

        hh_mgr = services.household_manager()
        household = hh_mgr.get(int(household_id)) if hh_mgr is not None else None
        if household is None:
            try:
                return bool(
                    hh_mgr.try_add_pending_household_funds(int(household_id), int(amount), int(reason))
                )
            except Exception:
                return False
        amount = int(amount)
        if amount > 0:
            household.funds.add(amount, reason, count_as_earnings=False)
            return True
        if amount < 0:
            return bool(household.funds.try_remove(-amount, reason))
        return True
    except Exception:
        return False
    finally:
        _applying_funds = False


@MessageHandler(KIND_MODIFY_HOUSEHOLD_FUNDS)
def _host_modify_household_funds(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    _apply_household_funds(
        body.get("amount", 0),
        body.get("household_id", 0),
        body.get("reason", 0),
    )


@MessageHandler(KIND_INVENTORY_SELL_MULTIPLE)
def _host_inventory_sell_multiple(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    msg_s = body.get("msg") or ""
    if not msg_s:
        return
    try:
        from google.protobuf import text_format
        from protocolbuffers import UI_pb2
        import services
        from distributor.ops import GenericProtocolBufferOp, SendUIMessage
        from protocolbuffers.DistributorOps_pb2 import Operation
    except Exception:
        # Fallback: try calling the original command with the opaque string.
        try:
            from server_commands import inventory_commands

            inventory_commands.sim_inventory_sell_multiple(msg_s)
        except Exception:
            return
        return

    try:
        sell_req = UI_pb2.InventorySellRequest()
        text_format.Merge(msg_s, sell_req)
    except Exception:
        return

    try:
        sim_info = services.sim_info_manager().get(sell_req.sim_id)
        if sim_info is None:
            return
        sim = sim_info.get_sim_instance()
        if sim is None:
            return
        inv = sim.inventory_component
        if inv is None:
            return
    except Exception:
        return

    total = 0
    to_destroy = []
    sold = []
    tags = set()
    try:
        stack_map = inv.get_stack_items_map(sell_req.stacks) if sell_req.stacks else {}
        for stack_id in list(sell_req.stacks or []):
            items = stack_map.get(stack_id) or []
            for obj in items:
                if getattr(obj, "non_deletable_by_user", False):
                    break
                total += obj.current_value * obj.stack_count()
                to_destroy.append(obj)
                sold.append(obj)
                tags.update(set(obj.get_tags()))

        inv_mgr = services.inventory_manager()
        storage = inv._storage
        updates = []
        for item in list(sell_req.items or []):
            item_id = getattr(item, "id", None)
            count = int(getattr(item, "count", 0) or 0)
            if item_id is None or item_id not in inv:
                continue
            obj = inv_mgr.get(item_id)
            if obj is None or getattr(obj, "non_deletable_by_user", False):
                continue
            total += obj.current_value * count
            obj.update_stack_count(-count)
            if obj.stack_count() < 1:
                to_destroy.append(obj)
            else:
                try:
                    update = storage._get_inventory_update_message(
                        UI_pb2.InventoryItemUpdate.TYPE_UPDATE, obj
                    )
                    if update is not None:
                        updates.append(GenericProtocolBufferOp(Operation.INVENTORY_ITEM_UPDATE, update))
                except Exception:
                    pass
            sold.append(obj)
            tags.update(obj.get_tags())

        if sold:
            hh = services.active_household()
            if hh is not None:
                from protocolbuffers import Consts_pb2

                reason = getattr(Consts_pb2, "TELEMETRY_OBJECT_SELL", 0)
                hh.add_currency_amount(
                    sell_req.currency_type,
                    total,
                    reason,
                    sim_info,
                    tags=frozenset(tags),
                )
            for obj in sold:
                try:
                    inv.publish_sell_from_inventory_telemetry(obj.definition.tuning_file_id)
                except Exception:
                    pass
            if to_destroy:
                services.get_reset_and_delete_service().trigger_batch_destroy(to_destroy)

        # Notify requesting joiner UI; host Distributor also picks it up.
        try:
            from simmp_client.deep.game_network import send_message_over_network
            from protocolbuffers import Consts_pb2

            # SendUIMessage is an op; prefer distributor on host.
            from distributor.system import Distributor

            Distributor.instance().add_op_with_no_owner(SendUIMessage("InventorySellItemsComplete"))
            for op in updates:
                Distributor.instance().add_op_with_no_owner(op)
        except Exception:
            pass
    except Exception:
        return


@MessageHandler(KIND_PURCHASE_PICKER_RESPONSE)
def _host_purchase_picker_response(wrapper):
    """Replay purchase picker on the host via the original inventory command."""
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from server_commands import inventory_commands
        from server_commands.argument_helpers import RequiredTargetParam
        from simmp_client.deep import dialogs as deep_dialogs

        ids = json.loads(body.get("ids_json") or "[]")
        if not isinstance(ids, list):
            ids = []
        player_id = int(body.get("player_id") or 0)
        deep_dialogs.waiting_for_callback_player_id = player_id or None
        try:
            inventory_commands.purchase_picker_response_by_ids(
                RequiredTargetParam(str(int(body.get("inventory_target") or 0))),
                RequiredTargetParam(str(int(body.get("inventory_source") or 0))),
                int(body.get("currency_type") or 0),
                int(body.get("dialog_id") or 0),
                int(body.get("delivery_method") or 0),
                1 if body.get("object_ids_or_definition_ids") else 0,
                *[int(x) for x in ids],
            )
        except TypeError:
            # Signature drift across patches: fall back to positional-only best effort.
            try:
                inventory_commands.purchase_picker_response_by_ids(
                    int(body.get("inventory_target") or 0),
                    int(body.get("inventory_source") or 0),
                    int(body.get("currency_type") or 0),
                    int(body.get("dialog_id") or 0),
                    int(body.get("delivery_method") or 0),
                    bool(body.get("object_ids_or_definition_ids")),
                    *[int(x) for x in ids],
                )
            except Exception:
                return
        except Exception:
            return
        finally:
            deep_dialogs.waiting_for_callback_player_id = None
    except Exception:
        return


@MessageHandler(KIND_INVENTORY_VIEW_UPDATE)
def _host_inventory_view_update(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    obj_id = int(body.get("obj_id") or 0)
    player_id = int(body.get("player_id") or 0)
    if not obj_id:
        return
    try:
        import services
        from protocolbuffers import UI_pb2
        from distributor.ops import GenericProtocolBufferOp
        from protocolbuffers.DistributorOps_pb2 import Operation
        from simmp_client.deep.game_network import send_message_over_network
        from protocolbuffers import Consts_pb2

        obj = services.current_zone().find_object(obj_id)
        if obj is None:
            return
        inv = obj.inventory_component
        if inv is None:
            return
        storage = inv._storage
        for item in storage:
            try:
                if getattr(item, "new_in_inventory", False):
                    item.new_in_inventory = False
                if item.id not in storage._objects:
                    continue
                update = storage._get_inventory_update_message(
                    UI_pb2.InventoryItemUpdate.TYPE_UPDATE, item
                )
                if update is None:
                    continue
                # Prefer targeted fan-out when we have a Consts msg id; else distributor.
                try:
                    from distributor.system import Distributor

                    Distributor.instance().add_op_with_no_owner(
                        GenericProtocolBufferOp(Operation.INVENTORY_ITEM_UPDATE, update)
                    )
                except Exception:
                    pass
            except Exception:
                continue
        # Also poke original command for host-local UI.
        try:
            from server_commands import inventory_commands

            fn = getattr(inventory_commands, "inventory_view_update", None) or getattr(
                inventory_commands, "view_update", None
            )
            if fn is not None:
                fn(obj_id)
        except Exception:
            pass
    except Exception:
        return