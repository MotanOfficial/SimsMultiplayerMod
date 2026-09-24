"""Horse competition UI / assignee / start relays."""

from __future__ import division

from simmp.deep import (
    KIND_PICK_NEW_HORSE_ASSIGNEE,
    KIND_SHOW_HORSE_COMPETITION_UI,
    KIND_START_HORSE_COMPETITION,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION
from simmp_client.deep import dialogs as deep_dialogs


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
    text = str(value).strip().lower()
    return text in ("1", "true", "yes", "on")


def install_horse_competition_hooks():
    try:
        from horse_competitions import horse_competition_commands
    except Exception:
        return False

    ok = False

    show_fn = getattr(horse_competition_commands, "show_competition_selector_ui", None)
    if show_fn is None:
        show_fn = getattr(horse_competition_commands, "show_horse_competition_ui", None)
    if show_fn is not None:

        @Override(show_fn, role=Role.JOINER)
        def _show_ui_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SHOW_HORSE_COMPETITION_UI,
                {"player_id": int(SESSION.player_id or 0)},
            )
            return None

        ok = True

    pick_fn = getattr(horse_competition_commands, "pick_new_assignee", None)
    if pick_fn is not None:

        @Override(pick_fn, role=Role.JOINER)
        def _pick_assignee_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                comp_id = _as_int(args[0] if args else kwargs.get("current_competition_id"))
                cur_sim = args[1] if len(args) > 1 else kwargs.get("current_sim")
                cur_horse = args[2] if len(args) > 2 else kwargs.get("current_horse")
                for_horse = _as_bool(args[3] if len(args) > 3 else kwargs.get("for_horse", False))
                sim_i = -1 if cur_sim is None else _as_int(cur_sim, -1)
                horse_i = -1 if cur_horse is None else _as_int(cur_horse, -1)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_PICK_NEW_HORSE_ASSIGNEE,
                {
                    "current_competition_id": comp_id,
                    "current_sim": sim_i,
                    "current_horse": horse_i,
                    "for_horse": for_horse,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    start_fn = getattr(horse_competition_commands, "start_competition", None)
    if start_fn is not None:

        @Override(start_fn, role=Role.JOINER)
        def _start_comp_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                comp_id = _as_int(args[0] if args else kwargs.get("competition_id"))
                sel_sim = _as_int(args[1] if len(args) > 1 else kwargs.get("selected_sim"))
                sel_horse = _as_int(args[2] if len(args) > 2 else kwargs.get("selected_horse"))
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_START_HORSE_COMPETITION,
                {
                    "competition_id": comp_id,
                    "selected_sim": sel_sim,
                    "selected_horse": sel_horse,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


@MessageHandler(KIND_SHOW_HORSE_COMPETITION_UI)
def _host_show_horse_ui(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    prev = deep_dialogs.waiting_for_callback_player_id
    deep_dialogs.waiting_for_callback_player_id = int(body.get("player_id") or 0) or None
    try:
        from horse_competitions import horse_competition_commands
        import services

        show_fn = getattr(horse_competition_commands, "show_competition_selector_ui", None)
        if show_fn is not None:
            show_fn()
            return
        svc = services.get_horse_competition_service()
        if svc is not None and hasattr(svc, "show_competition_selector_ui"):
            svc.show_competition_selector_ui()
    except Exception:
        return
    finally:
        deep_dialogs.waiting_for_callback_player_id = prev


@MessageHandler(KIND_PICK_NEW_HORSE_ASSIGNEE)
def _host_pick_new_assignee(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    prev = deep_dialogs.waiting_for_callback_player_id
    deep_dialogs.waiting_for_callback_player_id = int(body.get("player_id") or 0) or None
    try:
        from horse_competitions import horse_competition_commands

        sim = body.get("current_sim")
        horse = body.get("current_horse")
        horse_competition_commands.pick_new_assignee(
            int(body.get("current_competition_id") or 0),
            None if sim is None or int(sim) < 0 else int(sim),
            None if horse is None or int(horse) < 0 else int(horse),
            bool(body.get("for_horse")),
        )
    except Exception:
        return
    finally:
        deep_dialogs.waiting_for_callback_player_id = prev


@MessageHandler(KIND_START_HORSE_COMPETITION)
def _host_start_competition(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services

        svc = services.get_horse_competition_service()
        if svc is None:
            return
        sim = services.sim_info_manager().get(int(body.get("selected_sim") or 0))
        horse = services.sim_info_manager().get(int(body.get("selected_horse") or 0))
        if sim is None or horse is None:
            return
        svc.start_competition(int(body.get("competition_id") or 0), sim, horse)
    except Exception:
        return
