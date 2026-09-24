"""Restaurant order / config relays (Dine Out).

Opaque ``sim_orders`` / ``config_data`` are EA Restaurant protobuf text or
string payloads from the joiner UI; host merges and mutates the zone director.
"""

from __future__ import division

from simmp.deep import (
    KIND_ORDER_FOR_TABLE,
    KIND_REFRESH_RESTAURANT_CONFIG,
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


def install_restaurant_hooks():
    try:
        from restaurants import restaurant_commands
    except Exception:
        return False

    ok = False

    order_fn = getattr(restaurant_commands, "order_for_table", None)
    if order_fn is not None:

        @Override(order_fn, role=Role.JOINER)
        def _order_for_table_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                sim_orders = args[0] if args else kwargs.get("sim_orders")
                data_s = str(sim_orders) if sim_orders is not None else ""
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_ORDER_FOR_TABLE,
                {
                    "sim_orders": data_s,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    refresh_fn = getattr(restaurant_commands, "refresh_configuration", None)
    if refresh_fn is None:
        refresh_fn = getattr(restaurant_commands, "refresh_restaurant_config", None)
    if refresh_fn is not None:

        @Override(refresh_fn, role=Role.JOINER)
        def _refresh_config_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                # Prefer live venue config bytes/text when available.
                import build_buy
                import services

                cfg = build_buy.get_current_venue_config(services.current_zone_id())
                if cfg is None:
                    cfg = args[0] if args else kwargs.get("config_data")
                if isinstance(cfg, (bytes, bytearray)):
                    try:
                        data_s = bytes(cfg).decode("latin-1")
                    except Exception:
                        data_s = str(cfg)
                else:
                    data_s = str(cfg) if cfg is not None else ""
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_REFRESH_RESTAURANT_CONFIG,
                {
                    "config_data": data_s,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


@MessageHandler(KIND_ORDER_FOR_TABLE)
def _host_order_for_table(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    data_s = body.get("sim_orders") or ""
    if not data_s:
        return
    try:
        from google.protobuf import text_format
        from protocolbuffers import Restaurant_pb2
        from restaurants.restaurant_tuning import get_restaurant_zone_director
        import services
        from sims4.protocol_buffer_utils import has_field

        director = get_restaurant_zone_director()
        if director is None:
            return
        orders_pb = Restaurant_pb2.SimOrders()
        text_format.Merge(data_s, orders_pb)
        pairs = [(o.sim_id, o.recipe_id) for o in orders_pb.sim_orders]
        if not pairs:
            return
        sim = services.object_manager().get(pairs[0][0])
        if sim is None:
            return
        director.order_for_table(pairs)
        groups = director.get_dining_groups_by_sim(sim)
        if groups:
            group = groups.pop() if hasattr(groups, "pop") else list(groups)[0]
            meal_cost = orders_pb.meal_cost if has_field(orders_pb, "meal_cost") else 0
            group.hold_ordered_cost(meal_cost)
    except Exception:
        return


@MessageHandler(KIND_REFRESH_RESTAURANT_CONFIG)
def _host_refresh_restaurant_config(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    data_s = body.get("config_data") or ""
    if not data_s:
        return
    try:
        from restaurants.restaurant_tuning import get_restaurant_zone_director, MenuPresets
        from protocolbuffers import Restaurant_pb2

        director = get_restaurant_zone_director()
        if director is None:
            return
        cfg = Restaurant_pb2.RestaurantConfiguration()
        # Prefer binary parse; fall back to text.
        try:
            raw = data_s.encode("latin-1")
            cfg.ParseFromString(raw)
        except Exception:
            from google.protobuf import text_format

            text_format.Merge(data_s, cfg)
        if cfg.HasField("attire_id"):
            director._attire_outfit_category = cfg.attire_id
        if getattr(director, "_business_manager", None) is not None:
            director._preset_id = MenuPresets.CUSTOMIZE
        elif cfg.HasField("preset_id"):
            director._preset_id = cfg.preset_id
        if (
            getattr(director, "_preset_id", None) == MenuPresets.CUSTOMIZE
            and cfg.HasField("custom_menu")
            and len(cfg.custom_menu.courses) > 0
        ):
            # Leave detailed custom-menu map to original when possible.
            try:
                from restaurants import restaurant_commands

                refresh = getattr(restaurant_commands, "refresh_configuration", None)
                if refresh is None:
                    refresh = getattr(restaurant_commands, "refresh_restaurant_config", None)
                if refresh is not None:
                    refresh()
            except Exception:
                pass
    except Exception:
        return
