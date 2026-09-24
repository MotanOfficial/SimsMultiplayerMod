"""Situation create / start / destroy / end-dialog deep relays.

Joiners open situation UI and confirm guest lists locally; intent is relayed to
the host, which owns SituationManager. UI replies (SituationPrepare, etc.) go
back via targeted GameNetworkMessage.
"""

from __future__ import division

import json

from simmp.deep import (
    KIND_CREATE_SITUATION,
    KIND_DESTROY_USER_FACING_SITUATION,
    KIND_SHOW_END_SITUATION_DIALOG,
    KIND_START_SITUATION_CREATION,
    KIND_START_SITUATION_CREATION_FOR_EDIT,
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


def _player_sim_id(player_id):
    try:
        from simmp_client.deep import sim_select

        return sim_select.get_active_sim_id_for_player(player_id)
    except Exception:
        return None


def _send_situation_prepare(prep_pb, player_id):
    if not player_id:
        return
    try:
        from protocolbuffers import Consts_pb2
        from simmp_client.deep.game_network import send_message_over_network

        msg_id = getattr(Consts_pb2, "MSG_SITUATION_PREPARE", None)
        if msg_id is None:
            return
        send_message_over_network(msg_id, prep_pb, int(player_id))
    except Exception:
        return


def _parse_guest_args(guest_args_json):
    try:
        raw = json.loads(guest_args_json or "[]")
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        try:
            out.append(str(item))
        except Exception:
            continue
    return out


def install_situation_hooks():
    try:
        from server_commands import situation_commands
    except Exception:
        return False

    ok = False

    create_fn = getattr(situation_commands, "create_situation_with_guest_list", None)
    if create_fn is not None:

        @Override(create_fn, role=Role.JOINER)
        def _create_situation_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                situation_type = args[0]
                situation_type_id = int(getattr(situation_type, "guid64", situation_type))
                scoring_enabled = _as_bool_flag(args[1]) if len(args) > 1 else False
                zone_id = int(args[2]) if len(args) > 2 else 0
                scheduled_time = int(args[3]) if len(args) > 3 else 0
                drama_node_uid = int(args[4]) if len(args) > 4 else 0
                activity_ids = args[5] if len(args) > 5 else ""
                guest_style = args[6] if len(args) > 6 else 0
                guest_color = args[7] if len(args) > 7 else 0
                guest_style_i = int(getattr(guest_style, "value", guest_style) or 0)
                guest_color_i = int(getattr(guest_color, "value", guest_color) or 0)
                # Remaining positional args after known kwargs are guest triples.
                guest_tail = list(args[8:]) if len(args) > 8 else []
                # Also accept *args captured via kwargs leftover is uncommon.
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_CREATE_SITUATION,
                {
                    "situation_type": situation_type_id,
                    "scoring_enabled": scoring_enabled,
                    "zone_id": zone_id,
                    "scheduled_time": scheduled_time,
                    "drama_node_uid": drama_node_uid,
                    "activity_ids": str(activity_ids or ""),
                    "guest_style": guest_style_i,
                    "guest_color": guest_color_i,
                    "guest_args_json": json.dumps([str(x) for x in guest_tail]),
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    start_fn = getattr(situation_commands, "start_situation_creation", None)
    if start_fn is not None:

        @Override(start_fn, role=Role.JOINER)
        def _start_situation_creation_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                opt_sim = args[0] if args else None
                creation_time = int(args[1]) if len(args) > 1 and args[1] is not None else 0
                situation_category = int(args[2]) if len(args) > 2 and args[2] is not None else 0
                sim_id = int(getattr(opt_sim, "id", opt_sim) if opt_sim is not None else 0)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_START_SITUATION_CREATION,
                {
                    "sim_id": sim_id,
                    "creation_time": creation_time,
                    "situation_category": situation_category,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    edit_fn = getattr(situation_commands, "start_situation_creation_for_edit", None)
    if edit_fn is not None:

        @Override(edit_fn, role=Role.JOINER)
        def _start_situation_creation_for_edit_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                opt_sim = args[0] if args else None
                drama_node_uid = args[1] if len(args) > 1 else -1
                if opt_sim is None:
                    opt_sim_i = -1
                else:
                    opt_sim_i = int(getattr(opt_sim, "id", opt_sim))
                drama_i = int(drama_node_uid) if drama_node_uid is not None else -1
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_START_SITUATION_CREATION_FOR_EDIT,
                {
                    "opt_sim": opt_sim_i,
                    "drama_node_uid": drama_i,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    destroy_fn = getattr(situation_commands, "destroy_user_facing_situation", None)
    if destroy_fn is not None:

        @Override(destroy_fn, role=Role.JOINER)
        def _destroy_user_facing_situation_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                situation_id = int(args[0]) if args and args[0] is not None else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_DESTROY_USER_FACING_SITUATION,
                {
                    "situation_id": situation_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    end_fn = getattr(situation_commands, "show_end_situation_dialog", None)
    if end_fn is not None:

        @Override(end_fn, role=Role.JOINER)
        def _show_end_situation_dialog_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                situation_id = int(args[0])
                user_facing_type = int(args[1]) if len(args) > 1 else 0
                has_stayed_late = _as_bool_flag(args[2]) if len(args) > 2 else False
                time_token = int(args[3]) if len(args) > 3 and args[3] is not None else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SHOW_END_SITUATION_DIALOG,
                {
                    "situation_id": situation_id,
                    "user_facing_type": user_facing_type,
                    "has_stayed_late": has_stayed_late,
                    "time_token": time_token,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


def _build_guest_list(situation_type, host_sim_id, guest_args):
    from situations.situation_guest_list import (
        SituationGuestInfo,
        SituationGuestList,
        SituationInvitationPurpose,
    )
    from sims4.resources import Types
    import services

    force_invite = bool(getattr(situation_type, "force_invite_only", False))
    guest_list = SituationGuestList(force_invite, int(host_sim_id or 0))
    if len(guest_args) % 3 != 0:
        return None
    job_mgr = services.get_instance_manager(Types.SITUATION_JOB)
    for job_id_s, sim_id_s, purpose_s in zip(guest_args[0::3], guest_args[1::3], guest_args[2::3]):
        try:
            job = job_mgr.get(int(job_id_s))
            sim_id = int(sim_id_s)
            purpose = SituationInvitationPurpose(purpose_s)
        except Exception:
            return None
        if job is None:
            return None
        guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(sim_id, job, purpose))
    try:
        guest_list = situation_type.get_extended_guest_list(guest_list=guest_list)
    except Exception:
        pass
    return guest_list


@MessageHandler(KIND_CREATE_SITUATION)
def _host_create_situation(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    try:
        import services
        from sims4.resources import Types
        from server_commands import argument_helpers
        from tag import Tag
        from date_and_time import DateAndTime
    except Exception:
        return

    try:
        situation_type = argument_helpers.get_tunable_instance(
            Types.SITUATION, int(body.get("situation_type") or 0)
        )
    except Exception:
        situation_type = None
    if situation_type is None:
        return

    host_sim_id = _player_sim_id(player_id) or 0
    try:
        sim_info = services.sim_info_manager().get(host_sim_id) if host_sim_id else None
        if sim_info is not None and getattr(sim_info, "household", None) is not None:
            sim_info.household.set_situation_scoring(bool(body.get("scoring_enabled")))
    except Exception:
        pass

    guest_args = _parse_guest_args(body.get("guest_args_json"))
    guest_list = _build_guest_list(situation_type, host_sim_id, guest_args)
    if guest_list is None:
        return

    scheduled_time = int(body.get("scheduled_time") or 0)
    drama_node_uid = int(body.get("drama_node_uid") or 0) or None
    activity_raw = body.get("activity_ids") or ""
    if activity_raw in ("", "0"):
        activity_ids = None
    else:
        try:
            activity_ids = [int(x) for x in str(activity_raw).split(",") if x]
        except Exception:
            activity_ids = None

    try:
        mgr = services.get_zone_situation_manager()
        when = DateAndTime(scheduled_time) if scheduled_time else None
        mgr.create_situation(
            situation_type,
            guest_list=guest_list,
            zone_id=int(body.get("zone_id") or 0),
            scoring_enabled=bool(body.get("scoring_enabled")),
            scheduled_time=when,
            existing_drama_node_uid=drama_node_uid,
            activity_id_list=activity_ids,
            guest_attire_style=Tag(int(body.get("guest_style") or 0)),
            guest_attire_color=Tag(int(body.get("guest_color") or 0)),
        )
    except Exception:
        return


@MessageHandler(KIND_START_SITUATION_CREATION)
def _host_start_situation_creation(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    sim_id = int(body.get("sim_id") or 0)
    if not sim_id:
        sim_id = _player_sim_id(player_id) or 0
    if not sim_id:
        return
    try:
        import services
        from protocolbuffers import Situations_pb2

        mgr = services.get_zone_situation_manager()
        prep = Situations_pb2.SituationPrepare()
        prep.situation_session_id = mgr.get_new_situation_creation_session()
        prep.creation_time = int(body.get("creation_time") or 0)
        prep.sim_id = int(sim_id)
        prep.situation_category = int(body.get("situation_category") or 0)
        _send_situation_prepare(prep, player_id)
    except Exception:
        return


@MessageHandler(KIND_START_SITUATION_CREATION_FOR_EDIT)
def _host_start_situation_creation_for_edit(wrapper):
    """Best-effort edit entry: open a prepare session for the player's sim.

    Full drama-node seed packing is game-version fragile; missing APIs no-op.
    """
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    opt_sim = int(body.get("opt_sim") if body.get("opt_sim") is not None else -1)
    sim_id = opt_sim if opt_sim != -1 else (_player_sim_id(player_id) or 0)
    if not sim_id:
        return
    try:
        import services
        from protocolbuffers import Situations_pb2

        mgr = services.get_zone_situation_manager()
        prep = Situations_pb2.SituationPrepare()
        prep.situation_session_id = mgr.get_new_situation_creation_session()
        prep.sim_id = int(sim_id)
        drama_uid = int(body.get("drama_node_uid") if body.get("drama_node_uid") is not None else -1)
        if drama_uid != -1:
            try:
                node = services.drama_scheduler_service().get_scheduled_node_by_uid(drama_uid)
                if node is not None:
                    seed = getattr(node, "get_situation_seed", lambda: None)()
                    if seed is not None:
                        sit_type = getattr(seed, "situation_type", None) or getattr(node, "get_situation_type", lambda: None)()
                        if sit_type is not None:
                            prep.situation_resource_id.append(int(sit_type.guid64))
                            prep.situation_category = int(getattr(sit_type, "category", 0) or 0)
                    edit = prep.edit_data
                    edit.drama_node_id = int(drama_uid)
            except Exception:
                pass
        _send_situation_prepare(prep, player_id)
    except Exception:
        return


@MessageHandler(KIND_DESTROY_USER_FACING_SITUATION)
def _host_destroy_user_facing_situation(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    situation_id = int(body.get("situation_id") or 0)
    try:
        import services

        mgr = services.get_zone_situation_manager()
        if situation_id == 0:
            for sit in tuple(mgr.get_user_facing_situations_gen()):
                try:
                    mgr.destroy_situation_by_id(sit.id)
                except Exception:
                    continue
            return
        sit = mgr.get(situation_id)
        if sit is None:
            return
        if not getattr(sit, "is_user_facing", True):
            return
        mgr.destroy_situation_by_id(sit.id)
    except Exception:
        return


@MessageHandler(KIND_SHOW_END_SITUATION_DIALOG)
def _host_show_end_situation_dialog(wrapper):
    """Host opens the end-situation dialog for the requesting player's sim.

    Dialog responses flow back through the P6 dialog relays.
    """
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    situation_id = int(body.get("situation_id") or 0)
    player_id = int(body.get("player_id") or 0)
    if not situation_id:
        return
    try:
        import services
        from objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED
        from simmp_client.deep import dialogs as deep_dialogs

        mgr = services.get_zone_situation_manager()
        sit = mgr.get(situation_id)
        if sit is None or not getattr(sit, "is_user_facing", False):
            return
        sim_id = _player_sim_id(player_id)
        if not sim_id:
            return
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
        # Prefer calling the original command on the host so EA builds the dialog.
        from server_commands import situation_commands

        deep_dialogs.waiting_for_callback_player_id = player_id or None
        try:
            fn = situation_commands.show_end_situation_dialog
            # Pass through tokens the joiner provided when possible.
            fn(
                situation_id,
                int(body.get("user_facing_type") or 0),
                "1" if body.get("has_stayed_late") else "0",
                int(body.get("time_token") or 0) or None,
                sim,
            )
        except TypeError:
            try:
                fn(situation_id, _connection=None)
            except Exception:
                return
        except Exception:
            return
        finally:
            deep_dialogs.waiting_for_callback_player_id = None
    except Exception:
        return