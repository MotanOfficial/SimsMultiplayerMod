"""Career command relays (joiner UI -> host career tracker).

Core surface: send/leave work, find/select career, stay late, follow-enabled,
and career-event scoring dialog close (post-event travel).
"""

from __future__ import division

from simmp.deep import (
    KIND_CAREER_EVENT_SCORING_CLOSE,
    KIND_FIND_CAREER,
    KIND_LEAVE_WORK,
    KIND_SELECT_CAREER,
    KIND_SEND_TO_WORK,
    KIND_SET_FOLLOW_ENABLED,
    KIND_STAY_LATE,
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


def install_career_hooks():
    try:
        from server_commands import career_commands
    except Exception:
        return False

    ok = False

    send_fn = getattr(career_commands, "send_to_work", None)
    if send_fn is not None:

        @Override(send_fn, role=Role.JOINER)
        def _send_to_work_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                sim_id = _sim_id_from_arg(args[0] if args else None)
                career_uid = int(getattr(args[1], "guid64", args[1])) if len(args) > 1 else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SEND_TO_WORK,
                {
                    "sim_id": sim_id,
                    "career_uid": career_uid,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    leave_fn = getattr(career_commands, "leave_work", None)
    if leave_fn is not None:

        @Override(leave_fn, role=Role.JOINER)
        def _leave_work_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                # Signature is often (career_type, sim_id) per open-source fill order.
                career_uid = int(getattr(args[0], "guid64", args[0])) if args else 0
                sim_id = _sim_id_from_arg(args[1] if len(args) > 1 else None)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_LEAVE_WORK,
                {
                    "sim_id": sim_id,
                    "career_uid": career_uid,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    find_fn = getattr(career_commands, "find_career", None)
    if find_fn is not None:

        @Override(find_fn, role=Role.JOINER)
        def _find_career_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                sim_id = _sim_id_from_arg(args[0] if args else None)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_FIND_CAREER,
                {
                    "sim_id": sim_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    select_fn = getattr(career_commands, "select_career", None)
    if select_fn is None:
        select_fn = getattr(career_commands, "select", None)
    if select_fn is not None:

        @Override(select_fn, role=Role.JOINER)
        def _select_career_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                sim_id = _sim_id_from_arg(args[0] if args else None)
                career_instance_id = int(args[1]) if len(args) > 1 else 0
                track_id = int(args[2]) if len(args) > 2 else 0
                level = int(args[3]) if len(args) > 3 and args[3] is not None else 0
                company = int(args[4]) if len(args) > 4 and args[4] is not None else 0
                reason = int(getattr(args[5], "value", args[5])) if len(args) > 5 and args[5] is not None else 0
                shift = int(getattr(args[6], "value", args[6])) if len(args) > 6 and args[6] is not None else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SELECT_CAREER,
                {
                    "sim_id": sim_id,
                    "career_instance_id": career_instance_id,
                    "track_id": track_id,
                    "level": level,
                    "company_name_hash": company,
                    "reason": reason,
                    "schedule_shift_type": shift,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    stay_fn = getattr(career_commands, "stay_late", None)
    if stay_fn is not None:

        @Override(stay_fn, role=Role.JOINER)
        def _stay_late_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_STAY_LATE,
                {"player_id": int(SESSION.player_id or 0)},
            )
            return None

        ok = True

    follow_fn = getattr(career_commands, "set_follow_enabled", None)
    if follow_fn is not None:

        @Override(follow_fn, role=Role.JOINER)
        def _set_follow_enabled_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                sim_id = _sim_id_from_arg(args[0] if args else None)
                career_uid = int(args[1]) if len(args) > 1 else 0
                enabled = _as_bool_flag(args[2]) if len(args) > 2 else False
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SET_FOLLOW_ENABLED,
                {
                    "sim_id": sim_id,
                    "career_uid": career_uid,
                    "enabled": enabled,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    score_fn = getattr(career_commands, "on_career_event_scoring_dialog_close", None)
    if score_fn is not None:

        @Override(score_fn, role=Role.JOINER)
        def _career_event_scoring_close_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                sim_id = _sim_id_from_arg(args[0] if args else None)
                if not sim_id:
                    sim_id = -1
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_CAREER_EVENT_SCORING_CLOSE,
                {
                    "sim_id": sim_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


@MessageHandler(KIND_SEND_TO_WORK)
def _host_send_to_work(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    career_uid = int(body.get("career_uid") or 0)
    if not sim_id or not career_uid:
        return
    try:
        import services

        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        career = sim_info.career_tracker.get_career_by_uid(career_uid)
        if career is None:
            return
        if career.can_work_early():
            career.go_to_work_early()
            return
        if not sim_info.career_tracker.available_for_work(career):
            return
        career.put_sim_in_career_rabbit_hole()
    except Exception:
        return


@MessageHandler(KIND_LEAVE_WORK)
def _host_leave_work(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    career_uid = int(body.get("career_uid") or 0)
    if not sim_id or not career_uid:
        return
    try:
        import services
        from server_commands import argument_helpers
        from sims4.resources import Types

        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        career_type = None
        try:
            career_type = argument_helpers.get_tunable_instance(Types.CAREER, str(career_uid))
        except Exception:
            career_type = None
        uid = int(career_type.guid64) if career_type is not None else career_uid
        career = sim_info.career_tracker.get_career_by_uid(uid)
        if career is None:
            career = sim_info.career_tracker.get_career_by_uid(career_uid)
        if career is not None and getattr(career, "is_work_time", False):
            career.leave_work_early()
    except Exception:
        return


@MessageHandler(KIND_FIND_CAREER)
def _host_find_career(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    if not sim_id:
        return
    try:
        import services
        from careers.career_tuning import Career
        from interactions.context import InteractionContext, QueueInsertStrategy
        from interactions.priority import Priority

        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        sim = sim_info.get_sim_instance()
        if sim is None:
            return
        affordance = Career.FIND_JOB_PHONE_INTERACTION
        if sim.queue.has_duplicate_super_affordance(affordance, sim, None):
            return
        ctx = InteractionContext(
            sim,
            InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT,
            Priority.High,
            insert_strategy=QueueInsertStrategy.NEXT,
        )
        sim.push_super_affordance(affordance, sim, ctx)
    except Exception:
        return


@MessageHandler(KIND_SELECT_CAREER)
def _host_select_career(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    career_instance_id = int(body.get("career_instance_id") or 0)
    track_id = int(body.get("track_id") or 0)
    level = int(body.get("level") or 0)
    reason = int(body.get("reason") or 0)
    shift = int(body.get("schedule_shift_type") or 0)
    if not sim_id or not career_instance_id or not track_id:
        return
    try:
        import services
        import sims4.resources
        from careers.career_ops import CareerOps
        from rewards.reward_enums import RewardType

        career_mgr = services.get_instance_manager(sims4.resources.Types.CAREER)
        track_mgr = services.get_instance_manager(sims4.resources.Types.CAREER_TRACK)
        career_tuning = career_mgr.get(career_instance_id)
        track = track_mgr.get(track_id)
        sim_info = services.sim_info_manager().get(sim_id)
        if career_tuning is None or track is None or sim_info is None:
            return
        tracker = sim_info.career_tracker
        join = getattr(CareerOps, "JOIN_CAREER", 0)
        quit_op = getattr(CareerOps, "QUIT_CAREER", 1)
        if reason == join or reason == int(getattr(join, "value", join)):
            existing = tracker.get_career_by_uid(career_instance_id)
            if existing is not None:
                existing.on_branch_selection(track)
                return
            if level >= len(track.career_levels):
                return
            career = career_tuning(sim_info)
            tracker.add_career(
                career,
                show_confirmation_dialog=True,
                schedule_shift_override=shift,
                career_level_override=track.career_levels[level],
                disallowed_reward_types=(RewardType.MONEY,),
            )
        elif reason == quit_op or reason == int(getattr(quit_op, "value", quit_op)):
            tracker.remove_career(career_instance_id)
    except Exception:
        return


@MessageHandler(KIND_STAY_LATE)
def _host_stay_late(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    try:
        import services

        career = services.get_career_service().get_career_in_career_event()
        if career is not None:
            career.extend_career_session()
    except Exception:
        return


@MessageHandler(KIND_SET_FOLLOW_ENABLED)
def _host_set_follow_enabled(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    career_uid = int(body.get("career_uid") or 0)
    if not sim_id or not career_uid:
        return
    try:
        import services

        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        career = sim_info.career_tracker.get_career_by_uid(career_uid)
        if career is None:
            return
        career.follow_enabled = bool(body.get("enabled"))
        sim_info.career_tracker.resend_career_data()
    except Exception:
        return


@MessageHandler(KIND_CAREER_EVENT_SCORING_CLOSE)
def _host_career_event_scoring_close(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") if body.get("sim_id") is not None else -1)
    if sim_id == -1 or not sim_id:
        return
    try:
        import services
        from careers.career_event_manager import CareerEventManager

        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        CareerEventManager.post_career_event_travel(sim_info)
    except Exception:
        return