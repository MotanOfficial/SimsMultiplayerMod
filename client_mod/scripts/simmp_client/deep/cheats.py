"""Generic cheat command relay (rosebud / motherlode / skills / careers / …).

Joiners relay a CheatMessage-shaped body; host dispatches by cheat_name onto
the authoritative sim/household state.
"""

from __future__ import division

from simmp.deep import KIND_CHEAT, WrapperMessage
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION
from simmp_client.deep import sim_select


def _relay_cheat(cheat_name, sim_id=0, int_param=0, bool_param=False, str1="", str2=""):
    wrapper = WrapperMessage(
        target_client=int(SESSION.host_player_id or 0),
        kind=KIND_CHEAT,
        body={
            "cheat_name": cheat_name,
            "sim_id": int(sim_id or 0),
            "int_param": int(int_param or 0),
            "bool_param": bool(bool_param),
            "str_param_1": str(str1 or ""),
            "str_param_2": str(str2 or ""),
            "player_id": int(SESSION.player_id or 0),
        },
    )
    return SESSION.send_wrapper(wrapper, route="host")


def _active_sim_id():
    try:
        import services

        client = services.get_first_client()
        if client is None:
            return 0
        info = getattr(client, "active_sim_info", None)
        if info is None:
            sim = getattr(client, "active_sim", None)
            if sim is None:
                return 0
            return int(sim.id)
        return int(info.id)
    except Exception:
        return 0


def _as_bool_cheat(value):
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    try:
        from sims4.commands import BOOL_TRUE

        return value in BOOL_TRUE
    except Exception:
        text = str(value).strip().lower()
        return text in ("1", "true", "yes", "on", "t")


def install_cheat_hooks():
    ok = False

    # money cheats
    try:
        from server_commands import sim_commands
    except Exception:
        sim_commands = None

    if sim_commands is not None:
        for attr, name in (
            ("rosebud", "rosebud"),
            ("kaching", "rosebud"),
            ("motherlode", "motherlode"),
        ):
            fn = getattr(sim_commands, attr, None)
            if fn is None:
                continue

            def _make_money(cheat_name, target=fn):
                @Override(target, role=Role.JOINER)
                def _joiner(original, *args, **kwargs):
                    if not SESSION.enabled or SESSION.is_host:
                        return original(*args, **kwargs)
                    _relay_cheat(cheat_name, sim_id=_active_sim_id())
                    return None

                return _joiner

            _make_money(name)
            ok = True

        reset_fn = getattr(sim_commands, "reset_sim", None)
        if reset_fn is not None:

            @Override(reset_fn, role=Role.JOINER)
            def _reset_sim_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                first = args[0] if args else kwargs.get("first_name", "")
                last = args[1] if len(args) > 1 else kwargs.get("last_name", "")
                _relay_cheat("resetsim", str1=str(first or ""), str2=str(last or ""))
                return None

            ok = True

        fill_fn = getattr(sim_commands, "set_commodities_to_best_values", None)
        if fill_fn is not None:

            @Override(fill_fn, role=Role.JOINER)
            def _fill_commodities_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                visible = args[0] if args else kwargs.get("visible_only", True)
                _relay_cheat(
                    "fill_all_commodities",
                    bool_param=(str(visible).lower() != "false"),
                )
                return None

            ok = True

        sat_fn = getattr(sim_commands, "give_satisfaction_points", None)
        if sat_fn is not None:

            @Override(sat_fn, role=Role.JOINER)
            def _give_sat_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                points = args[0] if args else kwargs.get("satisfaction_points", 0)
                _relay_cheat(
                    "give_satisfaction_points",
                    sim_id=_active_sim_id(),
                    int_param=int(points or 0),
                )
                return None

            ok = True

    try:
        from server_commands import cheat_commands
    except Exception:
        cheat_commands = None

    if cheat_commands is not None:
        test_fn = getattr(cheat_commands, "testing_cheats", None)
        if test_fn is not None:

            @Override(test_fn, role=Role.JOINER)
            def _testing_cheats_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                enable = args[0] if args else kwargs.get("enable")
                _relay_cheat("testingcheats", bool_param=_as_bool_cheat(enable))
                return None

            ok = True

    try:
        from server_commands import aspiration_commands
    except Exception:
        aspiration_commands = None

    if aspiration_commands is not None:
        mile_fn = getattr(aspiration_commands, "complete_current_milestone", None)
        if mile_fn is not None:

            @Override(mile_fn, role=Role.JOINER)
            def _milestone_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                _relay_cheat("complete_current_milestone", sim_id=_active_sim_id())
                return None

            ok = True

    try:
        from server_commands import statistic_commands
    except Exception:
        statistic_commands = None

    if statistic_commands is not None:
        motive_fn = getattr(statistic_commands, "fill_motive", None)
        if motive_fn is not None:

            @Override(motive_fn, role=Role.JOINER)
            def _fill_motive_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                stat = args[0] if args else kwargs.get("stat_type")
                _relay_cheat(
                    "fillmotive",
                    sim_id=_active_sim_id(),
                    str1=str(stat) if stat is not None else "",
                )
                return None

            ok = True

        skill_fn = getattr(statistic_commands, "set_skill_level", None)
        if skill_fn is not None:

            @Override(skill_fn, role=Role.JOINER)
            def _set_skill_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                stat = args[0] if args else kwargs.get("stat_type")
                level = args[1] if len(args) > 1 else kwargs.get("level")
                if stat is None or level is None:
                    return False
                _relay_cheat(
                    "set_skill_level",
                    sim_id=_active_sim_id(),
                    str1=str(stat),
                    int_param=int(level),
                )
                return True

            ok = True

    try:
        from server_commands import career_commands
    except Exception:
        career_commands = None

    if career_commands is not None:
        for attr, name in (
            ("career_promote_sim", "careers.promote"),
            ("add_career_to_sim", "careers.add_career"),
            ("remove_career_from_sim", "careers.remove_career"),
            ("career_retire_sim", "careers.retire"),
        ):
            fn = getattr(career_commands, attr, None)
            if fn is None:
                continue

            def _make_career(cheat_name, target):
                @Override(target, role=Role.JOINER)
                def _joiner(original, *args, **kwargs):
                    if not SESSION.enabled or SESSION.is_host:
                        return original(*args, **kwargs)
                    career_type = args[0] if args else kwargs.get("career_type")
                    if career_type is None and cheat_name == "careers.add_career":
                        return False
                    _relay_cheat(
                        cheat_name,
                        sim_id=_active_sim_id(),
                        str1=str(career_type) if career_type is not None else "",
                    )
                    return True if cheat_name == "careers.add_career" else None

                return _joiner

            _make_career(name, fn)
            ok = True

    return ok


def _resolve_sim(sim_id, player_id):
    try:
        import services

        if sim_id:
            obj = services.object_manager().get(int(sim_id))
            if obj is not None:
                return obj
            info = services.sim_info_manager().get(int(sim_id))
            if info is not None:
                return getattr(info, "get_sim_instance", lambda: None)() or info
        if player_id:
            return sim_select.get_active_sim_for_player(player_id)
    except Exception:
        return None
    return None


@MessageHandler(KIND_CHEAT)
def _host_cheat(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    name = body.get("cheat_name") or ""
    sim_id = int(body.get("sim_id") or 0)
    player_id = int(body.get("player_id") or 0)
    int_param = int(body.get("int_param") or 0)
    bool_param = bool(body.get("bool_param"))
    str1 = body.get("str_param_1") or ""
    str2 = body.get("str_param_2") or ""

    try:
        import services
        from protocolbuffers import Consts_pb2
        from server_commands import sim_commands, argument_helpers
        from sims4.resources import Types

        sim = _resolve_sim(sim_id, player_id)
        info = None
        if sim is not None:
            info = getattr(sim, "sim_info", sim)

        if name in ("rosebud", "kaching"):
            target = info
            sim_commands.modify_fund_helper(1000, Consts_pb2.TELEMETRY_MONEY_CHEAT, target)
        elif name == "motherlode":
            target = info
            sim_commands.modify_fund_helper(50000, Consts_pb2.TELEMETRY_MONEY_CHEAT, target)
        elif name == "testingcheats":
            from server_commands.cheat_commands import _testing_cheats_common

            client = services.get_first_client()
            conn = int(getattr(client, "id", 0) or 0) if client else 0
            _testing_cheats_common(enable=bool_param, _connection=conn)
        elif name == "resetsim":
            from objects import ALL_HIDDEN_REASONS
            from objects.object_enums import ResetReason

            si = services.sim_info_manager().get_sim_info_by_name(str1, str2)
            if si is not None:
                inst = si.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                if inst is not None:
                    inst.reset(ResetReason.RESET_EXPECTED, None, "Command")
        elif name == "fill_all_commodities":
            for si in services.sim_info_manager().objects:
                si.commodity_tracker.set_all_commodities_to_best_value(
                    visible_only=bool_param
                )
        elif name == "give_satisfaction_points":
            if info is not None:
                from protocolbuffers.DistributorOps_pb2 import SetWhimBucks

                info.apply_satisfaction_points_delta(int_param, SetWhimBucks.COMMAND)
        elif name == "fillmotive":
            if sim is not None and str1:
                stat = argument_helpers.get_tunable_instance(Types.STATISTIC, str1)
                if stat is not None:
                    tracker = sim.get_tracker(stat)
                    tracker.set_value(stat, stat.max_value)
        elif name == "set_skill_level":
            if sim is not None and str1:
                from server_commands import statistic_commands

                stat = argument_helpers.get_tunable_instance(Types.STATISTIC, str1)
                client = services.get_first_client()
                conn = int(getattr(client, "id", 0) or 0) if client else 0
                statistic_commands._set_skill_level(stat, int_param, sim, conn)
        elif name == "careers.promote":
            if info is not None and str1:
                career_type = argument_helpers.get_tunable_instance(Types.CAREER, str1)
                if career_type is not None:
                    career = info.career_tracker.get_career_by_uid(career_type.guid64)
                    if career is not None:
                        career.promote()
        elif name == "careers.add_career":
            if info is not None and str1 and sim is not None:
                career_type = argument_helpers.get_tunable_instance(Types.CAREER, str1)
                if career_type is not None:
                    info.career_tracker.add_career(career_type(sim))
        elif name == "careers.remove_career":
            if info is not None and str1:
                career_type = argument_helpers.get_tunable_instance(Types.CAREER, str1)
                if career_type is not None:
                    info.career_tracker.remove_career(career_type.guid64)
        elif name == "careers.retire":
            if info is not None and str1:
                career_type = argument_helpers.get_tunable_instance(Types.CAREER, str1)
                if career_type is not None:
                    info.career_tracker.retire_career(career_type.guid64)
        elif name == "complete_current_milestone":
            # Replay original when available.
            try:
                from server_commands import aspiration_commands

                aspiration_commands.complete_current_milestone()
            except Exception:
                return
    except Exception:
        return
