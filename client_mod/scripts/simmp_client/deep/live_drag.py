"""Live-drag command relays (joiner -> host -> response).

Joiner intercepts live_drag.start / end / c_api_live_drag_end and
Client.sell_live_drag_object. Host starts/ends/sells on the real objects and
replies with start/end/sell response protobufs so the joiner UI stays in sync.
"""

from __future__ import division

import json

from simmp.deep import (
    KIND_LIVE_DRAG_END,
    KIND_LIVE_DRAG_END_RESPONSE,
    KIND_LIVE_DRAG_SELL,
    KIND_LIVE_DRAG_SELL_RESPONSE,
    KIND_LIVE_DRAG_START,
    KIND_LIVE_DRAG_START_RESPONSE,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.session import SESSION


def _as_bool_flag(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value) in ("1", "True", "true")


def _pack_transform(transform):
    """Extract translation/orientation floats from a Sims Transform-like object."""
    out = {"tx": 0.0, "ty": 0.0, "tz": 0.0, "ox": 0.0, "oy": 0.0, "oz": 0.0, "ow": 1.0}
    if transform is None:
        return out
    try:
        t = getattr(transform, "translation", None)
        if t is not None:
            out["tx"] = float(getattr(t, "x", t[0] if hasattr(t, "__getitem__") else 0.0))
            out["ty"] = float(getattr(t, "y", t[1] if hasattr(t, "__getitem__") else 0.0))
            out["tz"] = float(getattr(t, "z", t[2] if hasattr(t, "__getitem__") else 0.0))
        o = getattr(transform, "orientation", None)
        if o is not None:
            out["ox"] = float(getattr(o, "x", 0.0))
            out["oy"] = float(getattr(o, "y", 0.0))
            out["oz"] = float(getattr(o, "z", 0.0))
            out["ow"] = float(getattr(o, "w", 1.0))
    except Exception:
        pass
    return out


def _make_location(body):
    """Rebuild a sims4 Location from packed live-drag end fields."""
    try:
        import services
        from routing import SurfaceIdentifier
        from sims4.math import Location, Quaternion, Transform, Vector3
    except Exception:
        return None
    try:
        translation = Vector3(body.get("tx", 0.0), body.get("ty", 0.0), body.get("tz", 0.0))
        orientation = Quaternion(
            body.get("ox", 0.0),
            body.get("oy", 0.0),
            body.get("oz", 0.0),
            body.get("ow", 1.0),
        )
        transform = Transform(translation, orientation)
        surface = SurfaceIdentifier(
            services.current_zone_id(),
            body.get("routing_surface_secondary_id", 0),
            body.get("routing_surface_type", 0),
        )
        parent = None
        target_id = body.get("object_target_id") or 0
        if target_id:
            parent = services.current_zone().find_object(target_id)
        joint = body.get("joint_name_or_hash") or 0
        joint = None if joint == 0 else joint
        slot_hash = body.get("slot_hash") or 0
        if parent is not None:
            return Location(transform, surface, parent, joint, slot_hash)
        return Location(transform, surface)
    except Exception:
        return None


def _reply(kind, player_id, body):
    wrapper = WrapperMessage(
        target_client=int(player_id),
        client_id=int(SESSION.player_id or 0),
        kind=kind,
        body=body,
    )
    SESSION.send_wrapper(wrapper, route="player", target_player_id=int(player_id))


def install_live_drag_hooks():
    try:
        from server_commands import live_drag_commands
        from server.client import Client
    except Exception:
        return False

    from simmp_client.deep.override import Override, Role

    start_fn = getattr(live_drag_commands, "live_drag_start", None)
    end_fn = getattr(live_drag_commands, "live_drag_end", None)
    c_api_end = getattr(live_drag_commands, "c_api_live_drag_end", None)

    if start_fn is not None:

        @Override(start_fn, role=Role.JOINER)
        def _live_drag_start_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                object_id = int(args[0])
                start_system = int(args[1]) if len(args) > 1 else 0
                is_stack = _as_bool_flag(args[2]) if len(args) > 2 else False
                should_send = True
                if len(args) > 3:
                    should_send = bool(args[3]) if not isinstance(args[3], str) else _as_bool_flag(args[3])
                should_send = kwargs.get("should_send_start_message", should_send)
            except Exception:
                return original(*args, **kwargs)
            try:
                import services

                client = services.client_manager().get_first_client()
                if client is not None:
                    client._live_drag_is_stack = is_stack
            except Exception:
                pass
            wrapper = WrapperMessage(
                target_client=int(SESSION.host_player_id or 0),
                kind=KIND_LIVE_DRAG_START,
                body={
                    "live_drag_object_id": object_id,
                    "start_system": start_system,
                    "is_stack": is_stack,
                    "should_send_start_message": bool(should_send),
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            SESSION.send_wrapper(wrapper, route="host")
            return None

    if end_fn is not None:

        @Override(end_fn, role=Role.JOINER)
        def _live_drag_end_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                source_id = int(args[0])
                target_id = int(args[1]) if len(args) > 1 and args[1] is not None else 0
                end_system = int(args[2]) if len(args) > 2 else 0
            except Exception:
                return original(*args, **kwargs)
            is_stack = False
            try:
                import services

                client = services.client_manager().get_first_client()
                if client is not None:
                    is_stack = bool(getattr(client, "_live_drag_is_stack", False))
            except Exception:
                pass
            wrapper = WrapperMessage(
                target_client=int(SESSION.host_player_id or 0),
                kind=KIND_LIVE_DRAG_END,
                body={
                    "object_source_id": source_id,
                    "object_target_id": target_id,
                    "end_system": end_system,
                    "is_stack": is_stack,
                    "player_id": int(SESSION.player_id or 0),
                    "has_location": False,
                },
            )
            SESSION.send_wrapper(wrapper, route="host")
            return None

    if c_api_end is not None:

        @Override(c_api_end, role=Role.JOINER)
        def _c_api_live_drag_end_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            # (_, zone_id, obj_id, routing_surface, transform, parent_id, joint, slot_hash)
            try:
                obj_id = int(args[2])
                routing_surface = args[3]
                transform = args[4]
                parent_id = int(args[5]) if args[5] is not None else 0
                joint = args[6] if len(args) > 6 else 0
                slot_hash = int(args[7]) if len(args) > 7 and args[7] is not None else 0
            except Exception:
                return original(*args, **kwargs)
            is_stack = False
            end_system = 0
            try:
                import services
                from server.live_drag_tuning import LiveDragLocation

                client = services.client_manager().get_first_client()
                if client is not None:
                    is_stack = bool(getattr(client, "_live_drag_is_stack", False))
                end_system = int(LiveDragLocation.BUILD_BUY)
            except Exception:
                pass
            packed = _pack_transform(transform)
            secondary = 0
            surface_type = 0
            try:
                secondary = int(getattr(routing_surface, "secondary_id", 0) or 0)
                surface_type = int(getattr(routing_surface, "type", 0) or 0)
            except Exception:
                pass
            body = {
                "object_source_id": obj_id,
                "object_target_id": parent_id,
                "end_system": end_system,
                "is_stack": is_stack,
                "player_id": int(SESSION.player_id or 0),
                "has_location": True,
                "routing_surface_secondary_id": secondary,
                "routing_surface_type": surface_type,
                "joint_name_or_hash": int(joint) if joint is not None else 0,
                "slot_hash": slot_hash,
            }
            body.update(packed)
            wrapper = WrapperMessage(
                target_client=int(SESSION.host_player_id or 0),
                kind=KIND_LIVE_DRAG_END,
                body=body,
            )
            SESSION.send_wrapper(wrapper, route="host")
            return None

    sell_fn = getattr(Client, "sell_live_drag_object", None)
    if sell_fn is not None:

        @Override(sell_fn, role=Role.JOINER, target=Client, name="sell_live_drag_object")
        def _sell_live_drag_joiner(original, self, live_drag_object, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(self, live_drag_object, *args, **kwargs)
            try:
                end_system = int(kwargs.get("end_system", args[1] if len(args) > 1 else 0) or 0)
                currency_type = int(kwargs.get("currency_type", args[0] if args else 0) or 0)
            except Exception:
                currency_type = 0
                end_system = 0
            sim_id = 0
            try:
                if getattr(self, "active_sim", None) is not None:
                    sim_id = int(self.active_sim.id)
            except Exception:
                pass
            try:
                self._live_drag_sell_dialog_active = True
            except Exception:
                pass
            wrapper = WrapperMessage(
                target_client=int(SESSION.host_player_id or 0),
                kind=KIND_LIVE_DRAG_SELL,
                body={
                    "object_id": int(live_drag_object.id),
                    "end_system": end_system,
                    "is_stack": bool(getattr(self, "_live_drag_is_stack", False)),
                    "sim_id": sim_id,
                    "currency_type": currency_type,
                    "player_id": int(SESSION.player_id or 0),
                    "start_system": int(getattr(self, "_live_drag_start_system", 0) or 0),
                },
            )
            SESSION.send_wrapper(wrapper, route="host")
            return None

    return True


def _send_start_cancel(player_id, object_id, end_system=0):
    _reply(
        KIND_LIVE_DRAG_START_RESPONSE,
        player_id,
        {
            "live_drag_object_id": int(object_id),
            "start_system": 0,
            "end_system": int(end_system or 0),
            "cancel": True,
            "should_send_start_message": False,
        },
    )


@MessageHandler(KIND_LIVE_DRAG_START)
def _host_live_drag_start(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    object_id = int(body.get("live_drag_object_id") or 0)
    try:
        import services
        from distributor.shared_messages import create_icon_info_msg
    except Exception:
        return
    zone = services.current_zone()
    client = services.client_manager().get_first_client()
    if zone is None or client is None:
        return
    obj = zone.find_object(object_id)
    if obj is None:
        _send_start_cancel(player_id, object_id, body.get("start_system"))
        return
    is_stack = bool(body.get("is_stack"))
    start_system = int(body.get("start_system") or 0)
    stack_items = [obj]
    if is_stack:
        try:
            inv = obj.inventoryitem_component
            stack_id = inv.get_stack_id()
            inventory = inv.get_inventory()
            stack_items = list(inventory.get_stack_items(stack_id))
        except Exception:
            stack_items = [obj]
    started = False
    live_comp = None
    for item in stack_items:
        live_comp = getattr(item, "live_drag_component", None)
        if live_comp is None:
            _send_start_cancel(player_id, object_id, start_system)
            return
        try:
            in_use = getattr(item, "in_use", False)
            in_use_by = item.in_use_by(client) if hasattr(item, "in_use_by") else False
            can_drag = getattr(live_comp, "can_live_drag", True)
            if in_use and not in_use_by and not can_drag:
                _send_start_cancel(player_id, item.id, start_system)
                return
            started = bool(live_comp.start_live_dragging(client, start_system))
        except Exception:
            started = False
        if not started:
            break
    if not started:
        try:
            client.cancel_live_drag_on_objects()
        except Exception:
            pass
        _send_start_cancel(player_id, object_id, 0)
        return
    sell_value = -1
    try:
        if live_comp.active_household_has_sell_permission:
            sell_value = client.get_live_drag_object_value(obj, is_stack) if obj.definition.get_is_deletable() else -1
            for child in obj.get_all_children_gen():
                if child.definition.get_is_deletable():
                    sell_value += client.get_live_drag_object_value(child)
    except Exception:
        sell_value = -1
    drop_ids = []
    stack_id = 0
    try:
        drop_ids, stack_id = live_comp.get_valid_drop_object_ids()
        drop_ids = list(drop_ids or [])
    except Exception:
        drop_ids, stack_id = [], 0
    icon_bytes = b""
    try:
        icon_bytes = create_icon_info_msg(obj.get_icon_info_data()).SerializeToString()
    except Exception:
        icon_bytes = b""
    if body.get("should_send_start_message", True):
        _reply(
            KIND_LIVE_DRAG_START_RESPONSE,
            player_id,
            {
                "live_drag_object_id": int(obj.id),
                "start_system": start_system,
                "end_system": 0,
                "icon_info_msg": icon_bytes,
                "valid_drop_object_ids_json": json.dumps([int(x) for x in drop_ids]),
                "should_send_start_message": True,
                "valid_stack_id": int(stack_id or 0),
                "sell_value": int(sell_value),
                "cancel": False,
            },
        )


@MessageHandler(KIND_LIVE_DRAG_START_RESPONSE)
def _joiner_live_drag_start_response(wrapper):
    if not SESSION.enabled or SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services
        from distributor.ops import LiveDragStart
        from distributor.system import Distributor
        from protocolbuffers.UI_pb2 import IconInfo
        from server.live_drag_tuning import LiveDragLocation
    except Exception:
        return
    client = services.client_manager().get_first_client()
    if client is None:
        return
    if body.get("cancel"):
        try:
            client.send_live_drag_cancel(
                body.get("live_drag_object_id"),
                live_drag_end_system=body.get("end_system"),
            )
        except Exception:
            try:
                client.send_live_drag_cancel(body.get("live_drag_object_id"), body.get("end_system"))
            except Exception:
                pass
        return
    if not body.get("should_send_start_message"):
        return
    try:
        drop_ids = json.loads(body.get("valid_drop_object_ids_json") or "[]")
    except Exception:
        drop_ids = []
    icon = IconInfo()
    try:
        if body.get("icon_info_msg"):
            icon.ParseFromString(body.get("icon_info_msg"))
    except Exception:
        pass
    try:
        client._live_drag_start_system = LiveDragLocation(body.get("start_system"))
    except Exception:
        client._live_drag_start_system = body.get("start_system")
    try:
        op = LiveDragStart(
            body.get("live_drag_object_id"),
            body.get("start_system"),
            drop_ids,
            body.get("valid_stack_id"),
            body.get("sell_value"),
            icon,
        )
        Distributor.instance().add_op_with_no_owner(op)
    except Exception:
        return


@MessageHandler(KIND_LIVE_DRAG_END)
def _host_live_drag_end(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    try:
        import services
        from server.live_drag_tuning import LiveDragLocation
    except Exception:
        return
    zone = services.current_zone()
    client = services.client_manager().get_first_client()
    if zone is None or client is None:
        return
    source = zone.find_object(body.get("object_source_id"))
    if source is None:
        _reply(
            KIND_LIVE_DRAG_END_RESPONSE,
            player_id,
            {
                "success": False,
                "object_source_id": body.get("object_source_id"),
                "next_object_id": -1,
                "end_system": body.get("end_system"),
            },
        )
        return
    target = None
    location = None
    if body.get("has_location"):
        location = _make_location(body)
        if body.get("object_target_id"):
            target = zone.find_object(body.get("object_target_id"))
            if target is None:
                _reply(
                    KIND_LIVE_DRAG_END_RESPONSE,
                    player_id,
                    {
                        "success": False,
                        "object_source_id": body.get("object_source_id"),
                        "next_object_id": -1,
                        "end_system": body.get("end_system"),
                    },
                )
                return
    elif body.get("object_target_id"):
        target = zone.find_object(body.get("object_target_id"))
    try:
        if int(body.get("end_system") or 0) == int(LiveDragLocation.BUILD_BUY):
            client.objects_moved_via_live_drag.add(source)
        else:
            client.objects_moved_via_live_drag.discard(source)
    except Exception:
        pass
    success = False
    next_object_id = None
    is_stack = bool(body.get("is_stack"))
    try:
        if target is not None:
            drop_comp = getattr(target, "live_drag_target_component", None)
            if drop_comp is not None:
                success, next_object_id = drop_comp.drop_live_drag_object(source, is_stack)
            elif source.parent_object() is target:
                success = True
            elif source.parent_object() is None and location is not None:
                inv = getattr(source, "inventoryitem_component", None)
                if inv is not None and inv.is_in_inventory():
                    success, next_object_id = client.remove_drag_object_and_get_next_item(source)
                source.set_location(location)
                success = True
            else:
                success = False
        else:
            inv = getattr(source, "inventoryitem_component", None)
            if inv is not None and inv.is_in_inventory():
                success, next_object_id = client.remove_drag_object_and_get_next_item(source)
                if location is not None:
                    source.set_location(location)
            else:
                success, next_object_id = client.remove_drag_object_and_get_next_item(source)
                if location is not None:
                    source.set_location(location)
    except Exception:
        success = False
        next_object_id = None
    if not success and is_stack:
        next_object_id = None
    _reply(
        KIND_LIVE_DRAG_END_RESPONSE,
        player_id,
        {
            "success": bool(success),
            "object_source_id": body.get("object_source_id"),
            "next_object_id": int(next_object_id) if next_object_id is not None else -1,
            "end_system": body.get("end_system"),
        },
    )


@MessageHandler(KIND_LIVE_DRAG_END_RESPONSE)
def _joiner_live_drag_end_response(wrapper):
    if not SESSION.enabled or SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services
        from distributor.ops import LiveDragEnd
        from distributor.system import Distributor
        from server.live_drag_tuning import LiveDragLocation
    except Exception:
        return
    client = services.client_manager().get_first_client()
    if client is None:
        return
    try:
        client.cancel_live_drag_on_objects()
    except Exception:
        pass
    if body.get("success"):
        next_id = body.get("next_object_id")
        if next_id == -1:
            next_id = None
        try:
            op = LiveDragEnd(
                body.get("object_source_id"),
                LiveDragLocation.GAMEPLAY_UI,
                body.get("end_system"),
                next_id,
            )
            Distributor.instance().add_op_with_no_owner(op)
        except Exception:
            pass
    else:
        try:
            client.send_live_drag_cancel(body.get("object_source_id"), body.get("end_system"))
        except Exception:
            pass
    try:
        client._live_drag_is_stack = False
        client._live_drag_start_system = 0
    except Exception:
        pass


@MessageHandler(KIND_LIVE_DRAG_SELL)
def _host_live_drag_sell(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    try:
        import services
        from protocolbuffers import Consts_pb2
        from server.live_drag_tuning import LiveDragTuning
    except Exception:
        return
    zone = services.current_zone()
    client = services.client_manager().get_first_client()
    if zone is None or client is None:
        return
    obj = zone.find_object(body.get("object_id"))
    if obj is None:
        return
    sim_info = services.sim_info_manager().get(body.get("sim_id"))
    is_stack = bool(body.get("is_stack"))

    def _on_response(dialog):
        accepted = bool(getattr(dialog, "accepted", False))
        _reply(
            KIND_LIVE_DRAG_SELL_RESPONSE,
            player_id,
            {
                "object_id": int(obj.id),
                "end_system": body.get("end_system"),
                "start_system": body.get("start_system"),
                "accepted": accepted,
            },
        )
        if not accepted:
            return
        try:
            value = client.get_live_drag_object_value(obj, is_stack)
            for child in obj.get_all_children_gen():
                if child.definition.get_is_deletable():
                    value += client.get_live_drag_object_value(child)
            tags = set()
            if is_stack:
                _, stack_items = client._get_stack_items_from_drag_object(obj, remove=True, is_stack=True)
                for item in stack_items:
                    item.live_drag_component.cancel_live_dragging(should_reset=False)
                    item.base_value = 0
                    item.set_stack_count(0)
                    tags.update(item.get_tags())
                    item.destroy(item, "Selling stack of live drag objects.", source=item, cause="Selling stack of live drag objects.")
            else:
                obj.live_drag_component.cancel_live_dragging(should_reset=False)
                tags.update(obj.get_tags())
                if obj.is_in_inventory():
                    client.remove_drag_object_and_get_next_item(obj)
                else:
                    obj.remove_from_client()
                obj.base_value = 0
                obj.destroy(obj, "Selling live drag object.", source=obj, cause="Selling live drag object.")
            household = services.active_household()
            if household is not None and sim_info is not None:
                household.add_currency_amount(
                    body.get("currency_type"),
                    value,
                    Consts_pb2.TELEMETRY_OBJECT_SELL,
                    sim_info,
                    tags=frozenset(tags),
                )
        except Exception:
            return

    try:
        favorites = getattr(sim_info, "favorites_tracker", None) if sim_info is not None else None
        if favorites is not None and favorites.is_favorite_stack(obj):
            dialog = LiveDragTuning.LIVE_DRAG_SELL_FAVORITE_DIALOG(owner=obj)
        elif is_stack:
            dialog = LiveDragTuning.LIVE_DRAG_SELL_STACK_DIALOG(owner=obj)
        else:
            dialog = LiveDragTuning.LIVE_DRAG_SELL_DIALOG(owner=obj)
        dialog.show_dialog(on_response=_on_response)
    except Exception:
        # If no dialog API, auto-accept sell on host.
        class _Accepted(object):
            accepted = True

        _on_response(_Accepted())


@MessageHandler(KIND_LIVE_DRAG_SELL_RESPONSE)
def _joiner_live_drag_sell_response(wrapper):
    if not SESSION.enabled or SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services
        from distributor.ops import LiveDragEnd
        from distributor.system import Distributor
    except Exception:
        return
    client = services.client_manager().get_first_client()
    if client is None:
        return
    try:
        op = LiveDragEnd(body.get("object_id"), body.get("start_system"), body.get("end_system"), None)
        Distributor.instance().add_op_with_no_owner(op)
    except Exception:
        pass
    if not body.get("accepted"):
        try:
            client.cancel_live_drag_on_objects()
        except Exception:
            pass
        return
    try:
        client._live_drag_objects = None
        from server.live_drag_tuning import LiveDragLocation

        client._live_drag_start_system = LiveDragLocation.INVALID
        client._live_drag_is_stack = False
        client._live_drag_sell_dialog_active = False
    except Exception:
        try:
            client._live_drag_is_stack = False
            client._live_drag_sell_dialog_active = False
        except Exception:
            pass
