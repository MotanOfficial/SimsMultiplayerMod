"""Deep clock authority: joiner GameClock changes relay to the host.

Joiner: Override set_clock_speed / push_speed / pop_speed → protobuf to host.
Host: apply via game_clock_service. Host's own clock changes stay local and
are already fanned out through Client.send_message / GameNetworkMessage when
the distributor emits SetGameTime ops.

TIME_SYNC / force-pause apply through ``apply_clock_speed_local`` so the
joiner Override does not swallow authoritative room speed (that bug made
``Applied room speed 1 -> 0`` and left pause/unpause dead until mp.status).
"""

from simmp.deep import (
    CLOCK_METHOD_POP,
    CLOCK_METHOD_PUSH,
    CLOCK_METHOD_SET,
    KIND_SET_CLOCK_SPEED,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.session import SESSION


_IGNORED_PAUSE_REASONS = frozenset(
    (
        "Layout Manager Set Modal Visible",
        "travelMap",
        "igoUp",
        # Build/Buy must not pause the shared room clock for the other player.
        "build_buy",
        "BuildBuy",
        "build buy",
        "Build/Buy",
    )
)

# When True, joiner Overrides call through to the real GameClock APIs so
# multiplayer can apply an authoritative room speed locally.
_APPLYING_LOCAL = False


def apply_clock_speed_local(speed):
    """Set the local game clock, bypassing joiner deep Overrides.

    Returns the applied speed int, or None on failure.
    """
    global _APPLYING_LOCAL
    _APPLYING_LOCAL = True
    try:
        import services
        from clock import ClockSpeedMode

        game_clock = services.game_clock_service()
        if game_clock is None:
            return None
        speed_i = int(speed)
        mode = ClockSpeedMode(speed_i)
        # push_speed(PAUSED) barriers (build-buy / UI) survive a bare
        # set_clock_speed(NORMAL). Clear them before forcing a room resume so
        # joiners are not stuck paused after TIME_SYNC speed>=1.
        if speed_i > 0:
            pop = getattr(game_clock, "pop_speed", None)
            if pop is not None:
                for _ in range(8):
                    cur = getattr(game_clock, "clock_speed", None)
                    cur_i = int(getattr(cur, "value", cur) if cur is not None else -1)
                    if cur_i != 0:
                        break
                    try:
                        pop(ClockSpeedMode.PAUSED)
                    except TypeError:
                        try:
                            pop(ClockSpeedMode.PAUSED, reason="simmp_clear")
                        except Exception:
                            break
                    except Exception:
                        break
        setter = getattr(game_clock, "set_clock_speed", None)
        if setter is None:
            return None
        setter(mode)
        applied = getattr(game_clock, "clock_speed", None)
        return int(getattr(applied, "value", speed_i))
    except Exception:
        return None
    finally:
        _APPLYING_LOCAL = False


def _speed_int(speed):
    try:
        return int(getattr(speed, "value", speed))
    except Exception:
        return int(speed)


def _source_int(source):
    try:
        return int(getattr(source, "value", source) or 0)
    except Exception:
        return 0


def _send_clock(method, speed, source=0, reason="", immediate=False):
    reason = reason or ""
    if reason in _IGNORED_PAUSE_REASONS or "build" in str(reason).lower():
        return False
    wrapper = WrapperMessage(
        target_client=int(SESSION.host_player_id or 0),
        kind=KIND_SET_CLOCK_SPEED,
        body={
            "speed": _speed_int(speed) if speed is not None else 0,
            "immediate": bool(immediate),
            "source": _source_int(source),
            "reason": str(reason),
            "method": int(method),
            "player_id": int(SESSION.player_id or 0),
        },
    )
    return SESSION.send_wrapper(wrapper, route="host")


def install_clock_hooks():
    ok = False
    try:
        from clock import GameClock
    except Exception:
        GameClock = None

    from simmp_client.deep.override import Override, Role

    # Build/Buy normally force-pauses the lot. In co-op that freezes everyone
    # else; mirror the deep-multiplayer approach and no-op the command so only
    # the builder's local UI is affected (EA still greys the lot for them).
    try:
        from server_commands import clock_commands

        bb_fn = getattr(clock_commands, "build_buy_pause_unpause", None)
        if bb_fn is not None:

            @Override(bb_fn, role=Role.ALL)
            def _build_buy_pause_unpause(original, *args, **kwargs):
                if not SESSION.enabled:
                    return original(*args, **kwargs)
                return True

            ok = True
    except Exception:
        pass

    if GameClock is None:
        return ok

    @Override(GameClock.set_clock_speed, role=Role.JOINER)
    def _set_clock_speed_joiner(original, self, speed, *args, **kwargs):
        if _APPLYING_LOCAL or not SESSION.enabled or SESSION.is_host:
            return original(self, speed, *args, **kwargs)
        source = kwargs.get("source", args[0] if len(args) > 0 else 0)
        reason = kwargs.get("reason", args[1] if len(args) > 1 else "")
        immediate = kwargs.get("immediate", args[2] if len(args) > 2 else False)
        _send_clock(CLOCK_METHOD_SET, speed, source=source, reason=reason, immediate=immediate)
        # Apply locally too — otherwise the joiner UI pause button does nothing
        # until a TIME_SYNC round-trip (and that never arrives if the sync
        # alarm is asleep while paused).
        return original(self, speed, *args, **kwargs)

    @Override(GameClock.push_speed, role=Role.JOINER)
    def _push_speed_joiner(original, self, speed, *args, **kwargs):
        if _APPLYING_LOCAL or not SESSION.enabled or SESSION.is_host:
            return original(self, speed, *args, **kwargs)
        source = kwargs.get("source", args[0] if len(args) > 0 else 0)
        reason = kwargs.get("reason", args[2] if len(args) > 2 else (args[1] if len(args) > 1 else ""))
        if "reason" in kwargs:
            reason = kwargs["reason"]
        elif len(args) >= 3:
            reason = args[2]
        immediate = kwargs.get("immediate", args[3] if len(args) > 3 else False)
        if reason in _IGNORED_PAUSE_REASONS or "build" in str(reason).lower():
            return None
        _send_clock(CLOCK_METHOD_PUSH, speed, source=source, reason=reason, immediate=immediate)
        return original(self, speed, *args, **kwargs)

    @Override(GameClock.pop_speed, role=Role.JOINER)
    def _pop_speed_joiner(original, self, speed=None, *args, **kwargs):
        if _APPLYING_LOCAL or not SESSION.enabled or SESSION.is_host:
            return original(self, speed, *args, **kwargs) if speed is not None else original(self, *args, **kwargs)
        source = kwargs.get("source", args[0] if len(args) > 0 else 0)
        reason = kwargs.get("reason", args[1] if len(args) > 1 else "")
        immediate = kwargs.get("immediate", args[2] if len(args) > 2 else False)
        if reason in _IGNORED_PAUSE_REASONS or "build" in str(reason).lower():
            # Still clear a local pause barrier; just do not relay it.
            if speed is not None:
                return original(self, speed, *args, **kwargs)
            return original(self, *args, **kwargs)
        _send_clock(CLOCK_METHOD_POP, speed if speed is not None else 0, source=source, reason=reason, immediate=immediate)
        if speed is not None:
            return original(self, speed, *args, **kwargs)
        return original(self, *args, **kwargs)

    @Override(GameClock.push_speed, role=Role.HOST)
    def _push_speed_host(original, self, speed, *args, **kwargs):
        reason = kwargs.get("reason", args[2] if len(args) > 2 else (args[1] if len(args) > 1 else ""))
        if "reason" in kwargs:
            reason = kwargs["reason"]
        elif len(args) >= 3:
            reason = args[2]
        if SESSION.enabled and (reason in _IGNORED_PAUSE_REASONS or "build" in str(reason).lower()):
            return None
        return original(self, speed, *args, **kwargs)

    @Override(GameClock.pop_speed, role=Role.HOST)
    def _pop_speed_host(original, self, speed=None, *args, **kwargs):
        # Always allow pops so leftover pause barriers can clear.
        if speed is not None:
            return original(self, speed, *args, **kwargs)
        return original(self, *args, **kwargs)

    return True


def broadcast_absolute_game_time():
    """No-op placeholder — SetGameTime fan-out froze joiners on pause (M40).

    Absolute tick sync will return via a dedicated message, not Client.send_message.
    """
    return False


@MessageHandler(KIND_SET_CLOCK_SPEED)
def _host_set_clock_speed(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services
        from clock import ClockSpeedMode
    except Exception:
        return
    clock_service = services.game_clock_service()
    if clock_service is None:
        return
    speed_value = int(body.get("speed") or 0)
    try:
        speed = ClockSpeedMode(speed_value)
    except Exception:
        speed = speed_value
    method = int(body.get("method") or CLOCK_METHOD_SET)
    reason = body.get("reason") or ""
    # Ignore build-buy pause pushes only; always allow pops / explicit sets.
    if method == CLOCK_METHOD_PUSH and (
        reason in _IGNORED_PAUSE_REASONS or "build" in reason.lower()
    ):
        return
    immediate = bool(body.get("immediate"))
    source = body.get("source")
    try:
        if method == CLOCK_METHOD_PUSH:
            clock_service.push_speed(speed, source=source, reason=reason, immediate=immediate)
        elif method == CLOCK_METHOD_POP:
            clock_service.pop_speed(speed, source=source, reason=reason, immediate=immediate)
        else:
            clock_service.set_clock_speed(speed, source=source, reason=reason, immediate=immediate)
    except TypeError:
        try:
            if method == CLOCK_METHOD_PUSH:
                clock_service.push_speed(speed)
            elif method == CLOCK_METHOD_POP:
                clock_service.pop_speed(speed)
            else:
                clock_service.set_clock_speed(speed)
        except Exception:
            return
    except Exception:
        return
