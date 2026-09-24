"""University enroll + cancel-enrollment-dialog relays.

Joiners relay enrollment UI intent; host mutates degree_tracker / household funds.
"""

from __future__ import division

from simmp.deep import (
    KIND_CANCEL_ENROLLMENT_DIALOG,
    KIND_UNIVERSITY_ENROLL,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION
from simmp_client.deep import sim_select


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
    if isinstance(value, str) and value.strip() in ("None", "none", ""):
        return default
    try:
        return int(getattr(value, "guid64", getattr(value, "id", getattr(value, "value", value))))
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


def install_university_hooks():
    try:
        from sims.university import university_commands
    except Exception:
        try:
            from university import university_commands
        except Exception:
            return False

    ok = False

    enroll_fn = getattr(university_commands, "enroll", None)
    if enroll_fn is not None:

        @Override(enroll_fn, role=Role.JOINER)
        def _enroll_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                major = _as_int(args[0] if args else kwargs.get("major"))
                university = _as_int(args[1] if len(args) > 1 else kwargs.get("university"))
                opt_sim = _as_int(args[2] if len(args) > 2 else kwargs.get("opt_sim"))
                classes = _as_int(args[3] if len(args) > 3 else kwargs.get("classes"))
                elective_arg = args[4] if len(args) > 4 else kwargs.get("elective")
                if elective_arg is None or str(elective_arg) == "None":
                    elective = -1
                else:
                    elective = _as_int(elective_arg, -1)
                tuition = _as_int(args[5] if len(args) > 5 else kwargs.get("tuition_cost"))
                scholarship = _as_int(
                    args[6] if len(args) > 6 else kwargs.get("total_scholarship_taken")
                )
                using_loan = _as_bool(
                    args[7] if len(args) > 7 else kwargs.get("is_using_loan", False)
                )
                dest = args[8] if len(args) > 8 else kwargs.get("destination_zone_id")
                dest_id = -1 if dest is None else _as_int(dest, -1)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_UNIVERSITY_ENROLL,
                {
                    "major": major,
                    "university": university,
                    "opt_sim": opt_sim,
                    "classes": classes,
                    "elective": elective,
                    "tuition_cost": tuition,
                    "total_scholarship_taken": scholarship,
                    "is_using_loan": using_loan,
                    "destination_zone_id": dest_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    cancel_fn = getattr(university_commands, "cancel_enrollment_dialog", None)
    if cancel_fn is None:
        cancel_fn = getattr(university_commands, "on_cancel_enrollment_dialog", None)
    if cancel_fn is not None:

        @Override(cancel_fn, role=Role.JOINER)
        def _cancel_enrollment_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                opt_sim = _as_int(args[0] if args else kwargs.get("opt_sim"))
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_CANCEL_ENROLLMENT_DIALOG,
                {
                    "opt_sim": opt_sim,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


def _resolve_sim_info(opt_sim, player_id):
    try:
        import services

        if opt_sim:
            info = services.sim_info_manager().get(int(opt_sim))
            if info is not None:
                return info
        if player_id:
            return sim_select.get_active_sim_for_player(player_id)
    except Exception:
        return None
    return None


@MessageHandler(KIND_UNIVERSITY_ENROLL)
def _host_university_enroll(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from server_commands import argument_helpers
        from sims4.resources import Types
        from protocolbuffers import Consts_pb2

        major = argument_helpers.get_tunable_instance(
            Types.UNIVERSITY_MAJOR, int(body.get("major") or 0)
        )
        university = argument_helpers.get_tunable_instance(
            Types.UNIVERSITY, int(body.get("university") or 0)
        )
        elective_id = int(body.get("elective") if body.get("elective") is not None else -1)
        elective = None
        if elective_id != -1:
            elective = argument_helpers.get_tunable_instance(
                Types.UNIVERSITY_COURSE_DATA, elective_id
            )
        info = _resolve_sim_info(body.get("opt_sim"), body.get("player_id"))
        if info is None or major is None or university is None:
            return
        tracker = getattr(info, "degree_tracker", None)
        if tracker is None:
            return
        courses = () if elective is None else (elective,)
        classes = int(body.get("classes") or 0)
        try:
            tracker.enroll(major, university, classes, courses=courses)
        except TypeError:
            tracker.enroll(major, university, classes, courses)
        tuition = int(body.get("tuition_cost") or 0)
        if body.get("is_using_loan"):
            try:
                from sims.loan_tuning import LoanTunables, LoanType

                LoanTunables.add_debt(
                    info, LoanTunables.get_loan_amount(tuition, LoanType.UNIVERSITY)
                )
            except Exception:
                pass
        else:
            try:
                info.household.funds.try_remove(
                    tuition, Consts_pb2.FUNDS_TUITION_COST, info
                )
            except Exception:
                pass
        try:
            tracker.handle_scholarships_after_enrollment(
                int(body.get("total_scholarship_taken") or 0)
            )
        except Exception:
            pass
        dest = int(body.get("destination_zone_id") if body.get("destination_zone_id") is not None else -1)
        if dest >= 0:
            home = getattr(getattr(info, "household", None), "home_zone_id", None)
            if home == dest and hasattr(tracker, "on_enroll_in_same_housing"):
                tracker.on_enroll_in_same_housing()
    except Exception:
        return


@MessageHandler(KIND_CANCEL_ENROLLMENT_DIALOG)
def _host_cancel_enrollment_dialog(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    info = _resolve_sim_info(body.get("opt_sim"), body.get("player_id"))
    if info is None:
        return
    try:
        tracker = getattr(info, "degree_tracker", None)
        if tracker is None:
            return
        tracker.on_cancel_enrollment_dialog()
    except Exception:
        return
