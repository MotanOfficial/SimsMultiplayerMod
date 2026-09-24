"""Travel / zone spin-up deep relays.

- Joiners force-complete SimSpawnerService batch spawn during zone spin-up
  (host already simulates; joiners must not stall on staggered spawn).
- Loading-screen finish broadcasts KIND_TRAVEL_FINISHED; host unpauses clock
  and marks the session game-ready.
- Joiner travel_sims_to_zone / vacation commands relay to the host.
"""

from __future__ import division

import json

from simmp.deep import (
    KIND_END_VACATION,
    KIND_EXTEND_VACATION,
    KIND_TRAVEL_FINISHED,
    KIND_TRAVEL_SIMS_TO_ZONE,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION

# False while any client is mid-travel load; host clock UI should wait.
_game_ready = True
_finished_players = set()


def is_game_ready():
    return bool(_game_ready)


def _relay_to_host(kind, body):
    wrapper = WrapperMessage(
        target_client=int(SESSION.host_player_id or 0),
        kind=kind,
        body=body,
    )
    return SESSION.send_wrapper(wrapper, route="host")


def _broadcast(kind, body):
    wrapper = WrapperMessage(
        target_client=0,
        client_id=int(SESSION.player_id or 0),
        kind=kind,
        body=body,
    )
    return SESSION.send_wrapper(wrapper, route="broadcast")


def _current_zone_id():
    try:
        import services

        return int(services.current_zone_id())
    except Exception:
        return 0


def install_travel_hooks():
    ok = False

    # --- Zone spin-up: joiner must batch-spawn all pending sims immediately ---
    try:
        from sims.sim_spawner_service import SimSpawnerService, _SpawningMode
    except Exception:
        SimSpawnerService = None
        _SpawningMode = None

    if SimSpawnerService is not None:
        spawn_fn = getattr(SimSpawnerService, "batch_spawn_during_zone_spin_up", None)
        if spawn_fn is not None:

            @Override(spawn_fn, role=Role.JOINER, target=SimSpawnerService, name="batch_spawn_during_zone_spin_up")
            def _batch_spawn_joiner(original, self):
                if not SESSION.enabled or SESSION.is_host:
                    return original(self)
                try:
                    if _SpawningMode is not None:
                        self._mode = _SpawningMode.BATCH_SPAWNING
                    done = False
                    while not done:
                        done = not self._spawn_next_sim()
                    if _SpawningMode is not None:
                        self._mode = _SpawningMode.WAITING_HITTING_MARKS
                except Exception:
                    try:
                        return original(self)
                    except Exception:
                        return None
                return None

            ok = True

    # --- Loading screen finished: travel barrier ---
    try:
        from zone import Zone
    except Exception:
        Zone = None

    if Zone is not None:
        load_fn = getattr(Zone, "on_loading_screen_animation_finished", None)
        if load_fn is not None:

            @Override(load_fn, role=Role.ALL, target=Zone, name="on_loading_screen_animation_finished")
            def _loading_screen_finished(original, self, *args, **kwargs):
                global _game_ready
                result = original(self, *args, **kwargs)
                if not SESSION.enabled:
                    return result
                _game_ready = False
                _finished_players.clear()
                try:
                    import services
                    from clock import ClockSpeedMode

                    services.game_clock_service().set_clock_speed(ClockSpeedMode.PAUSED)
                except Exception:
                    pass
                body = {
                    "player_id": int(SESSION.player_id or 0),
                    "zone_id": _current_zone_id(),
                }
                if SESSION.is_host:
                    # Host still announces so joiners can mark local ready when
                    # they receive the fan-out after their own finish.
                    _on_local_travel_finished(body["player_id"], body["zone_id"])
                else:
                    _relay_to_host(KIND_TRAVEL_FINISHED, body)
                return result

            ok = True

    # --- Travel map: joiner relays zone travel to host ---
    try:
        from world import travel_commands
    except Exception:
        travel_commands = None

    if travel_commands is not None:
        travel_fn = getattr(travel_commands, "travel_sims_to_zone", None)
        if travel_fn is not None:

            @Override(travel_fn, role=Role.JOINER)
            def _travel_sims_to_zone_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    opt_sim = args[0] if args else None
                    zone_id = int(args[1]) if len(args) > 1 else 0
                    sim_ids = list(args[2:]) if len(args) > 2 else []
                    opt_sim_i = int(getattr(opt_sim, "id", opt_sim)) if opt_sim is not None else -1
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_TRAVEL_SIMS_TO_ZONE,
                    {
                        "opt_sim_id": opt_sim_i,
                        "zone_id": zone_id,
                        "traveling_sim_ids_json": json.dumps([int(x) for x in sim_ids]),
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        # Soft-block joiner travel availability / household info (host owns map).
        avail_fn = getattr(travel_commands, "get_sims_available_for_travel", None)
        if avail_fn is not None:

            @Override(avail_fn, role=Role.JOINER)
            def _get_sims_available_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                return False

            ok = True

        view_fn = getattr(travel_commands, "send_travel_view_household_info", None)
        if view_fn is not None:

            @Override(view_fn, role=Role.JOINER)
            def _send_travel_view_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                return False

            ok = True

    # --- Vacation travel groups ---
    try:
        from server_commands import travel_group_commands
    except Exception:
        travel_group_commands = None

    if travel_group_commands is not None:
        end_fn = getattr(travel_group_commands, "end_vacation", None)
        if end_fn is not None:

            @Override(end_fn, role=Role.JOINER)
            def _end_vacation_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    group_id = int(args[0]) if args else 0
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_END_VACATION,
                    {
                        "travel_group_id": group_id,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        extend_fn = getattr(travel_group_commands, "extend_vacation", None)
        if extend_fn is not None:

            @Override(extend_fn, role=Role.JOINER)
            def _extend_vacation_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    group_id = int(args[0]) if args else 0
                    duration = int(args[1]) if len(args) > 1 else 0
                    cost = int(args[2]) if len(args) > 2 else 0
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_EXTEND_VACATION,
                    {
                        "travel_group_id": group_id,
                        "duration_days": duration,
                        "cost": cost,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

    return ok


def _on_local_travel_finished(player_id, zone_id):
    global _game_ready
    if player_id:
        _finished_players.add(int(player_id))
    _game_ready = True
    if SESSION.is_host:
        try:
            import services
            from clock import ClockSpeedMode

            services.game_clock_service().set_clock_speed(ClockSpeedMode.NORMAL)
        except Exception:
            pass
        # Tell joiners travel barrier is clear.
        _broadcast(
            KIND_TRAVEL_FINISHED,
            {
                "player_id": int(SESSION.player_id or 0),
                "zone_id": int(zone_id or 0),
            },
        )


@MessageHandler(KIND_TRAVEL_FINISHED)
def _on_travel_finished(wrapper):
    global _game_ready
    if not SESSION.enabled:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    zone_id = int(body.get("zone_id") or 0)
    if SESSION.is_host:
        _on_local_travel_finished(player_id, zone_id)
        return
    # Joiner: host cleared the barrier.
    _game_ready = True
    if player_id:
        _finished_players.add(player_id)


@MessageHandler(KIND_TRAVEL_SIMS_TO_ZONE)
def _host_travel_sims_to_zone(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from world import travel_commands

        opt_sim = int(body.get("opt_sim_id") if body.get("opt_sim_id") is not None else -1)
        zone_id = int(body.get("zone_id") or 0)
        sim_ids = json.loads(body.get("traveling_sim_ids_json") or "[]")
        if not isinstance(sim_ids, list):
            sim_ids = []
        sim_ids = [int(x) for x in sim_ids]
        if opt_sim == -1:
            travel_commands.travel_sims_to_zone(None, zone_id, *sim_ids)
        else:
            travel_commands.travel_sims_to_zone(opt_sim, zone_id, *sim_ids)
    except Exception:
        return


@MessageHandler(KIND_END_VACATION)
def _host_end_vacation(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    group_id = int(body.get("travel_group_id") or 0)
    try:
        import services

        group = services.travel_group_manager().get(group_id)
        if group is None:
            return
        group.end_vacation()
    except Exception:
        return


@MessageHandler(KIND_EXTEND_VACATION)
def _host_extend_vacation(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    group_id = int(body.get("travel_group_id") or 0)
    duration = int(body.get("duration_days") or 0)
    cost = int(body.get("cost") or 0)
    try:
        import services

        group = services.travel_group_manager().get(group_id)
        if group is None:
            return
        if getattr(group, "is_vacation_over", False) and duration == 0:
            group.end_vacation()
        else:
            group.extend_vacation(duration, cost)
    except Exception:
        return