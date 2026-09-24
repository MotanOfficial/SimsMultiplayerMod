"""Pie-menu / interaction command relays (joiner -> host -> omega UI).

P0: generate_choices / select_choice / push_interaction
P1: has_choices (+ response glow), cancel_interaction, generate_phone_choices
"""

from simmp.deep import (
    KIND_CANCEL_INTERACTION,
    KIND_GENERATE_CHOICES,
    KIND_GENERATE_PHONE_CHOICES,
    KIND_HAS_CHOICES,
    KIND_HAS_CHOICES_RESPONSE,
    KIND_PUSH_INTERACTION,
    KIND_SELECT_CHOICE,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.session import SESSION
from simmp_client.deep import game_network


_choice_menus = {}


def _active_sim_id():
    try:
        import services

        client = services.get_first_client()
        if client is None or client.active_sim_info is None:
            return 0
        return int(client.active_sim_info.id)
    except Exception:
        return 0


def _as_bool_flag(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value) in ("1", "True", "true")


def _resolve_sim(sim_id):
    import services

    sim_info = services.sim_info_manager().get(sim_id)
    if sim_info is None:
        return None, None
    return sim_info, sim_info.get_sim_instance()


def _build_interactable(object_id, is_interactable, flags=0):
    from protocolbuffers.InteractionOps_pb2 import Interactable

    msg = Interactable()
    msg.object_id = int(object_id)
    msg.is_interactable = bool(is_interactable)
    try:
        msg.interactable_flags = int(flags)
    except Exception:
        pass
    return msg


def _perform_has_choices(body, client, zone):
    """Host-side interactable probe. Returns (immediate, Interactable)."""
    sim_id = body.get("sim_id")
    target_id = body.get("target_id")
    sim_info, sim = _resolve_sim(sim_id)
    if sim is None:
        return False, _build_interactable(target_id, False)

    try:
        import sims4
        from server_commands.interaction_commands import (
            _get_targets_from_pick,
            _get_interactable_flags,
        )
    except Exception:
        _get_interactable_flags = None
        try:
            import sims4
            from server_commands.interaction_commands import _get_targets_from_pick
        except Exception:
            return False, _build_interactable(target_id, False)

    location = sims4.math.Vector3(body.get("x", 0.0), body.get("y", 0.0), body.get("z", 0.0))
    target = zone.find_object(target_id)
    try:
        pick_target, pick_type, objects_and_surfaces = _get_targets_from_pick(
            sim,
            target,
            body.get("pick_type"),
            location,
            body.get("level"),
            zone.id,
            body.get("lot_id"),
            body.get("is_routable"),
            preferred_objects=set(),
        )
    except Exception:
        return False, _build_interactable(target_id, False)

    is_interactable = bool(objects_and_surfaces)
    flags = 0
    if is_interactable and _get_interactable_flags is not None:
        try:
            flags = _get_interactable_flags(sim, pick_target, objects_and_surfaces)
        except Exception:
            flags = 0
    return False, _build_interactable(target_id, is_interactable, flags)


def install_interaction_command_hooks():
    """Patch interaction_commands on joiners to relay intent to the host."""
    try:
        from server_commands import interaction_commands
    except Exception:
        return False

    from simmp_client.deep.override import Override, Role

    @Override(interaction_commands.generate_choices, role=Role.JOINER)
    def _generate_choices_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            target_id = int(args[0])
            pick_type = int(args[1])
            x = float(args[2])
            y = float(args[3])
            z = float(args[4])
            lot_id = int(args[5])
            level = int(args[6])
            shift = int(args[9]) if len(args) > 9 else 0
            reference_id = int(args[10]) if len(args) > 10 else 0
            is_routable = _as_bool_flag(args[13]) if len(args) > 13 else False
        except Exception:
            return original(*args, **kwargs)
        wrapper = WrapperMessage(
            target_client=int(SESSION.host_player_id or 0),
            kind=KIND_GENERATE_CHOICES,
            body={
                "target_id": target_id,
                "pick_type": pick_type,
                "x": x,
                "y": y,
                "z": z,
                "lot_id": lot_id,
                "level": level,
                "reference_id": reference_id,
                "is_routable": is_routable,
                "sim_id": _active_sim_id(),
                "player_id": int(SESSION.player_id or 0),
                "shift": shift,
            },
        )
        SESSION.send_wrapper(wrapper, route="host")
        return None

    @Override(interaction_commands.select_choice, role=Role.JOINER)
    def _select_choice_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            choice_id = int(args[0])
            reference_id = int(args[1])
        except Exception:
            return original(*args, **kwargs)
        wrapper = WrapperMessage(
            target_client=int(SESSION.host_player_id or 0),
            kind=KIND_SELECT_CHOICE,
            body={
                "choice_id": choice_id,
                "reference_id": reference_id,
                "sim_id": _active_sim_id(),
                "player_id": int(SESSION.player_id or 0),
            },
        )
        SESSION.send_wrapper(wrapper, route="host")
        return None

    @Override(interaction_commands.push_interaction, role=Role.JOINER)
    def _push_interaction_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            affordance = args[0]
            affordance_id = int(getattr(affordance, "guid64", affordance))
            opt_target = args[1] if len(args) > 1 else None
            opt_sim = args[2] if len(args) > 2 else None
            priority = args[3] if len(args) > 3 else 0
            opt_target_id = int(opt_target) if opt_target is not None else -1
            opt_sim_id = int(opt_sim) if opt_sim is not None else -1
            priority_i = int(getattr(priority, "value", priority) or 0)
        except Exception:
            return original(*args, **kwargs)
        wrapper = WrapperMessage(
            target_client=int(SESSION.host_player_id or 0),
            kind=KIND_PUSH_INTERACTION,
            body={
                "affordance": affordance_id,
                "opt_target": opt_target_id,
                "opt_sim": opt_sim_id,
                "priority": priority_i,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        SESSION.send_wrapper(wrapper, route="host")
        return None

    # --- P1: has_choices ---
    has_choices_fn = getattr(interaction_commands, "has_choices", None)
    if has_choices_fn is not None:

        @Override(has_choices_fn, role=Role.JOINER)
        def _has_choices_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                target_id = int(args[0]) if args[0] is not None else None
                if target_id is None:
                    return False
                pick_type = int(args[1]) if len(args) > 1 else 0
                x = float(args[2]) if len(args) > 2 else 0.0
                y = float(args[3]) if len(args) > 3 else 0.0
                z = float(args[4]) if len(args) > 4 else 0.0
                lot_id = int(args[5]) if len(args) > 5 else 0
                level = int(args[6]) if len(args) > 6 else 0
                control = _as_bool_flag(args[7]) if len(args) > 7 else False
                alt = _as_bool_flag(args[8]) if len(args) > 8 else False
                shift = _as_bool_flag(args[9]) if len(args) > 9 else False
                is_routable = _as_bool_flag(args[11]) if len(args) > 11 else True
            except Exception:
                return original(*args, **kwargs)
            wrapper = WrapperMessage(
                target_client=int(SESSION.host_player_id or 0),
                kind=KIND_HAS_CHOICES,
                body={
                    "target_id": target_id,
                    "pick_type": pick_type,
                    "x": x,
                    "y": y,
                    "z": z,
                    "lot_id": lot_id,
                    "level": level,
                    "control": control,
                    "alt": alt,
                    "shift": shift,
                    "is_routable": is_routable,
                    "sim_id": _active_sim_id(),
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            SESSION.send_wrapper(wrapper, route="host")
            # Returning True means "wait for async response" in EA's path when
            # networked; False would claim no choices. Prefer True so the glow
            # arrives via has_choices_response.
            return True

    # --- P1: cancel ---
    cancel_fn = None
    for name in ("cancel_super_interaction", "cancel_si", "cancel_interaction"):
        cancel_fn = getattr(interaction_commands, name, None)
        if cancel_fn is not None:
            break
    if cancel_fn is not None:

        @Override(cancel_fn, role=Role.JOINER)
        def _cancel_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                interaction_id = int(args[0])
                context_handle = int(args[1]) if len(args) > 1 else 0
            except Exception:
                return original(*args, **kwargs)
            wrapper = WrapperMessage(
                target_client=int(SESSION.host_player_id or 0),
                kind=KIND_CANCEL_INTERACTION,
                body={
                    "interaction_id": interaction_id,
                    "context_handle": context_handle,
                    "sim_id": _active_sim_id(),
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            SESSION.send_wrapper(wrapper, route="host")
            return None

    # --- P1: phone choices ---
    phone_fn = getattr(interaction_commands, "generate_phone_choices", None)
    if phone_fn is not None:

        @Override(phone_fn, role=Role.JOINER)
        def _phone_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            reference_id = 0
            selected = -1
            try:
                # Signature varies; prefer kwargs then positional tails.
                reference_id = int(kwargs.get("reference_id", args[3] if len(args) > 3 else 0) or 0)
                selected_raw = kwargs.get("selected_affordance_id", args[4] if len(args) > 4 else None)
                selected = int(selected_raw) if selected_raw is not None else -1
            except Exception:
                pass
            wrapper = WrapperMessage(
                target_client=int(SESSION.host_player_id or 0),
                kind=KIND_GENERATE_PHONE_CHOICES,
                body={
                    "sim_id": _active_sim_id(),
                    "player_id": int(SESSION.player_id or 0),
                    "reference_id": reference_id,
                    "selected_affordance_id": selected,
                },
            )
            SESSION.send_wrapper(wrapper, route="host")
            return None

    return True


@MessageHandler(KIND_GENERATE_CHOICES)
def _host_generate_choices(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    try:
        import services
        import sims4
        from interactions.choices import ChoiceMenu
        from protocolbuffers import Consts_pb2
        from server_commands.interaction_commands import (
            _get_targets_from_pick,
            create_pie_menu_message,
            should_generate_pie_menu,
            PieMenuActions,
        )
    except Exception:
        return

    zone = services.current_zone()
    client = services.get_first_client()
    if zone is None or client is None:
        return
    sim_info, sim = _resolve_sim(body.get("sim_id"))
    if sim is None:
        return
    target = zone.find_object(body.get("target_id"))
    choice_menu = ChoiceMenu(sim)
    shift = bool(body.get("shift"))
    pie_action = should_generate_pie_menu(client, sim, shift)
    show = pie_action == PieMenuActions.SHOW_PIE_MENU
    show_debug = pie_action == PieMenuActions.SHOW_DEBUG_PIE_MENU
    if show or show_debug:
        try:
            location = sims4.math.Vector3(body.get("x", 0.0), body.get("y", 0.0), body.get("z", 0.0))
            preferred = set()
            pick_target, pick_type, objects_and_surfaces = _get_targets_from_pick(
                sim,
                target,
                body.get("pick_type"),
                location,
                body.get("level"),
                zone.id,
                body.get("lot_id"),
                body.get("is_routable"),
                preferred_objects=preferred,
            )
            if pick_target is not None and objects_and_surfaces:
                from server.pick_info import PickInfo

                for obj, surface in objects_and_surfaces:
                    pick = PickInfo(
                        pick_type=pick_type,
                        target=obj,
                        location=location,
                        routing_surface=surface,
                        lot_id=body.get("lot_id"),
                        level=body.get("level"),
                        alt=False,
                        control=False,
                        shift=shift,
                    )
                    context = client.create_interaction_context(sim, pick=pick, shift_held=shift)
                    context.add_preferred_objects(preferred)
                    aops = list(obj.potential_interactions(context)) if hasattr(obj, "potential_interactions") else []
                    choice_menu.add_potential_aops(obj, context, aops, None)
        except Exception:
            pass
    _choice_menus[player_id] = choice_menu
    try:
        pie_msg = create_pie_menu_message(
            sim,
            choice_menu,
            body.get("reference_id"),
            pie_action,
            target=target,
            suppress_front_page=False,
        )
        game_network.send_message_over_network(Consts_pb2.MSG_PIE_MENU_CREATE, pie_msg, player_id)
    except Exception:
        return


@MessageHandler(KIND_SELECT_CHOICE)
def _host_select_choice(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    menu = _choice_menus.get(player_id)
    if menu is None:
        return
    if getattr(menu, "revision", None) != body.get("reference_id"):
        return
    item = menu.menu_items.get(body.get("choice_id"))
    if item is None:
        return
    try:
        if item.result and not getattr(item, "target_invalid", False):
            item.aop.test_and_execute(item.context)
    except Exception:
        return


@MessageHandler(KIND_PUSH_INTERACTION)
def _host_push_interaction(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services
        from interactions.context import InteractionContext
        from interactions.priority import Priority
        from sims4.resources import Types
    except Exception:
        return
    affordance_id = body.get("affordance")
    opt_sim = body.get("opt_sim", -1)
    opt_target = body.get("opt_target", -1)
    try:
        affordance = services.get_instance_manager(Types.INTERACTION).get(affordance_id)
    except Exception:
        affordance = None
    if affordance is None:
        return
    sim = None
    if opt_sim not in (-1, None):
        _, sim = _resolve_sim(opt_sim)
    if sim is None:
        client = services.get_first_client()
        sim = client.active_sim if client is not None else None
    if sim is None:
        return
    target = None
    if opt_target not in (-1, None):
        target = services.current_zone().find_object(opt_target)
    try:
        priority = Priority(body.get("priority") or Priority.High)
    except Exception:
        priority = Priority.High
    try:
        context = InteractionContext(sim, InteractionContext.SOURCE_PIE_MENU, priority)
        sim.push_super_affordance(affordance, target, context)
    except Exception:
        return


@MessageHandler(KIND_HAS_CHOICES)
def _host_has_choices(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    try:
        import services
    except Exception:
        return
    client = services.get_first_client()
    zone = services.current_zone()
    if client is None or zone is None:
        return
    try:
        immediate, interactable = _perform_has_choices(body, client, zone)
        raw = interactable.SerializeToString()
    except Exception:
        return
    reply = WrapperMessage(
        target_client=player_id,
        client_id=int(SESSION.player_id or 0),
        kind=KIND_HAS_CHOICES_RESPONSE,
        body={"immediate": bool(immediate), "msg": raw},
    )
    SESSION.send_wrapper(reply, route="player", target_player_id=player_id)


@MessageHandler(KIND_HAS_CHOICES_RESPONSE)
def _joiner_has_choices_response(wrapper):
    if not SESSION.enabled or SESSION.is_host:
        return
    body = wrapper.body or {}
    raw = body.get("msg") or b""
    if not raw:
        return
    try:
        from distributor.system import Distributor
        from protocolbuffers import Consts_pb2
        from protocolbuffers.InteractionOps_pb2 import Interactable

        interactable = Interactable()
        interactable.ParseFromString(raw)
        Distributor.instance().add_event(
            Consts_pb2.MSG_OBJECT_IS_INTERACTABLE,
            interactable,
            body.get("immediate", False),
        )
    except Exception:
        return


@MessageHandler(KIND_CANCEL_INTERACTION)
def _host_cancel_interaction(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services
        from server_commands.interaction_commands import send_reject_response
        from protocolbuffers import Sims_pb2 as SimsProtocols
    except Exception:
        send_reject_response = None
        SimsProtocols = None

    _, sim = _resolve_sim(body.get("sim_id"))
    if sim is None:
        return
    interaction_id = body.get("interaction_id")
    context_handle = body.get("context_handle")
    interaction = None
    try:
        interaction = sim.find_interaction_by_id(interaction_id)
    except Exception:
        interaction = None
    if interaction is None:
        try:
            continuation = sim.find_continuation_by_id(interaction_id)
        except Exception:
            continuation = None
        if continuation is not None:
            try:
                continuation.cancel_user(cancel_reason_msg="User canceled the interaction.")
            except Exception:
                pass
        return
    try:
        cancelled = interaction.cancel_user(cancel_reason_msg="Command interactions.cancel_si")
    except Exception:
        cancelled = False
    if cancelled:
        return
    if context_handle and send_reject_response is not None and SimsProtocols is not None:
        try:
            client = services.get_first_client()
            reject = SimsProtocols.ServerResponseFailed.REJECT_CLIENT_CANCEL_SUPERINTERACTION
            send_reject_response(client, sim, context_handle, reject)
        except Exception:
            return


@MessageHandler(KIND_GENERATE_PHONE_CHOICES)
def _host_generate_phone_choices(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    try:
        import services
        from interactions.choices import ChoiceMenu
        from protocolbuffers import Consts_pb2
        from server_commands.interaction_commands import (
            create_pie_menu_message,
            PieMenuActions,
        )
    except Exception:
        return

    client = services.get_first_client()
    if client is None:
        return
    sim_info, sim = _resolve_sim(body.get("sim_id"))
    if sim is None:
        return
    choice_menu = ChoiceMenu(sim)
    pie_action = PieMenuActions.SHOW_PIE_MENU
    try:
        if sim.queue is None or sim.queue.can_queue_visible_interaction():
            context = client.create_interaction_context(sim, shift_held=False)
            aops = list(sim.potential_phone_interactions(context))
            choice_menu.add_potential_aops(None, context, aops, None)
            _choice_menus[player_id] = choice_menu
        else:
            pie_action = PieMenuActions.INTERACTION_QUEUE_FULL_TOOLTIP
            _choice_menus[player_id] = None
    except Exception:
        _choice_menus[player_id] = choice_menu
    selected = body.get("selected_affordance_id", -1)
    if selected == -1:
        selected = None
    try:
        pie_msg = create_pie_menu_message(
            sim,
            choice_menu,
            body.get("reference_id"),
            pie_action,
            do_phone_tests=True,
            selected_affordance_id=selected,
        )
        game_network.send_message_over_network(Consts_pb2.MSG_PHONE_MENU_CREATE, pie_msg, player_id)
    except Exception:
        return
