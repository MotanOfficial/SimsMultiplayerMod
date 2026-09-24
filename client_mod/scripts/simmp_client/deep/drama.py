"""Drama / festival command relays (joiner calendar UI -> host scheduler).

Joiners relay festival info, travel-to-zone/event, and cancel-scheduled-node.
Host owns DramaSchedulerService and pushes travel affordances for the
requesting player's active sim.
"""

from __future__ import division

from simmp.deep import (
    KIND_CANCEL_SCHEDULED_DRAMA_NODE,
    KIND_SHOW_FESTIVAL_INFO,
    KIND_SHOW_FESTIVAL_INFO_BY_UID,
    KIND_TRAVEL_TO_EVENT,
    KIND_TRAVEL_TO_FESTIVAL_ZONE,
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


def _drama_node_id_from_arg(value):
    if value is None:
        return 0
    try:
        return int(getattr(value, "guid64", value))
    except Exception:
        return 0


def _player_sim(player_id):
    try:
        from objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED
        from simmp_client.deep import sim_select
        import services

        sim_id = sim_select.get_active_sim_id_for_player(player_id)
        if not sim_id:
            return None
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return None
        return sim_info.get_sim_instance(
            allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED
        )
    except Exception:
        return None


def install_drama_hooks():
    try:
        from server_commands import drama_commands
    except Exception:
        return False

    ok = False

    show_fn = getattr(drama_commands, "show_festival_info", None)
    if show_fn is not None:

        @Override(show_fn, role=Role.JOINER)
        def _show_festival_info_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                node_id = _drama_node_id_from_arg(args[0] if args else None)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SHOW_FESTIVAL_INFO,
                {
                    "drama_node_id": node_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    show_uid_fn = getattr(drama_commands, "show_festival_info_by_drama_node_uid", None)
    if show_uid_fn is not None:

        @Override(show_uid_fn, role=Role.JOINER)
        def _show_festival_info_by_uid_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                uid = int(args[0]) if args else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SHOW_FESTIVAL_INFO_BY_UID,
                {
                    "drama_node_uid": uid,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    travel_zone_fn = getattr(drama_commands, "travel_to_event_zone", None)
    if travel_zone_fn is not None:

        @Override(travel_zone_fn, role=Role.JOINER)
        def _travel_to_event_zone_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                node_id = _drama_node_id_from_arg(args[0] if args else None)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_TRAVEL_TO_FESTIVAL_ZONE,
                {
                    "drama_node_id": node_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    cancel_fn = getattr(drama_commands, "cancel_scheduled_node", None)
    if cancel_fn is not None:

        @Override(cancel_fn, role=Role.JOINER)
        def _cancel_scheduled_node_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                node_id = int(args[0]) if args else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_CANCEL_SCHEDULED_DRAMA_NODE,
                {
                    "drama_node_id": node_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    travel_event_fn = getattr(drama_commands, "travel_to_event", None)
    if travel_event_fn is not None:

        @Override(travel_event_fn, role=Role.JOINER)
        def _travel_to_event_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                zone_id = int(args[0]) if args else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_TRAVEL_TO_EVENT,
                {
                    "zone_id": zone_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


def _get_drama_node_tuning(drama_node_id):
    try:
        from server_commands import argument_helpers
        from sims4.resources import Types

        return argument_helpers.get_tunable_instance(Types.DRAMA_NODE, str(int(drama_node_id)))
    except Exception:
        return None


def _push_travel_to_lot(sim, lot_id, affordance):
    if sim is None or affordance is None or lot_id is None:
        return False
    try:
        from interactions.context import InteractionContext, QueueInsertStrategy
        from interactions.priority import Priority
        from server.pick_info import PickInfo, PickType

        pick = PickInfo(
            pick_type=PickType.PICK_TERRAIN,
            lot_id=lot_id,
            ignore_neighborhood_id=True,
        )
        ctx = InteractionContext(
            sim,
            InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT,
            Priority.High,
            insert_strategy=QueueInsertStrategy.NEXT,
            pick=pick,
        )
        sim.push_super_affordance(affordance, None, ctx)
        return True
    except Exception:
        return False


def _travel_to_drama_destination(drama_node, player_id):
    try:
        lot_id = drama_node.get_destination_lot_id()
    except Exception:
        try:
            lot_id = drama_node.get_travel_lot_id()
        except Exception:
            lot_id = None
    if lot_id is None:
        return
    try:
        affordance = drama_node.get_travel_interaction()
    except Exception:
        affordance = None
    sim = _player_sim(player_id)
    _push_travel_to_lot(sim, lot_id, affordance)


@MessageHandler(KIND_SHOW_FESTIVAL_INFO)
def _host_show_festival_info(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    node_id = int(body.get("drama_node_id") or 0)
    if not node_id:
        return
    try:
        from server_commands import drama_commands

        # Host runs the real command; Client.send_message fans UI to joiners.
        drama_commands.show_festival_info(node_id)
    except Exception:
        try:
            node = _get_drama_node_tuning(node_id)
            if node is None:
                return
            from server_commands import drama_commands

            drama_commands.show_festival_info(node)
        except Exception:
            return


@MessageHandler(KIND_SHOW_FESTIVAL_INFO_BY_UID)
def _host_show_festival_info_by_uid(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    uid = int(body.get("drama_node_uid") or 0)
    if not uid:
        return
    try:
        from server_commands import drama_commands

        drama_commands.show_festival_info_by_drama_node_uid(uid)
    except Exception:
        try:
            import services

            sched = services.drama_scheduler_service()
            node = sched.get_active_node_by_uid(uid)
            if node is None:
                node = sched.get_scheduled_node_by_uid(uid)
            if node is None:
                return
            from server_commands import drama_commands

            drama_commands.show_festival_info(node.guid64)
        except Exception:
            return


@MessageHandler(KIND_TRAVEL_TO_FESTIVAL_ZONE)
def _host_travel_to_festival_zone(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    node_id = int(body.get("drama_node_id") or 0)
    player_id = int(body.get("player_id") or 0)
    if not node_id:
        return
    try:
        from drama_scheduler.drama_node_types import DramaNodeType
        import services

        node = _get_drama_node_tuning(node_id)
        if node is None:
            return
        node_type = getattr(node, "drama_node_type", None)
        if node_type == DramaNodeType.FESTIVAL or str(node_type).endswith("FESTIVAL"):
            _travel_to_drama_destination(node, player_id)
            return
        # Venue events: prefer an active instance of the same guid.
        sched = services.drama_scheduler_service()
        if sched is None:
            return
        active = None
        try:
            for candidate in sched.active_nodes_gen():
                if int(getattr(candidate, "guid64", 0)) == int(getattr(node, "guid64", node_id)):
                    active = candidate
                    break
        except Exception:
            active = None
        _travel_to_drama_destination(active or node, player_id)
    except Exception:
        return


@MessageHandler(KIND_CANCEL_SCHEDULED_DRAMA_NODE)
def _host_cancel_scheduled_drama_node(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    node_id = int(body.get("drama_node_id") or 0)
    if not node_id:
        return
    try:
        import services

        services.drama_scheduler_service().cancel_scheduled_node(node_id)
    except Exception:
        return


@MessageHandler(KIND_TRAVEL_TO_EVENT)
def _host_travel_to_event(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    zone_id = int(body.get("zone_id") or 0)
    player_id = int(body.get("player_id") or 0)
    if not zone_id:
        return
    try:
        import services
        from venues.venue_event_drama_node import VenueEventDramaNode

        affordance = getattr(VenueEventDramaNode, "GO_TO_VENUE_ZONE_INTERACTION", None)
        if affordance is None:
            return
        lot_id = services.get_persistence_service().get_lot_id_from_zone_id(zone_id)
        sim = _player_sim(player_id)
        _push_travel_to_lot(sim, lot_id, affordance)
    except Exception:
        return