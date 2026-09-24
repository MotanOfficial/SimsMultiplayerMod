"""Lighting editor relays (show picker / set color+intensity).

Joiners relay lighting UI; host owns light mutations and color-picker dialogs.
"""

from __future__ import division

from simmp.deep import (
    KIND_SET_COLOR_AND_INTENSITY,
    KIND_SHOW_LIGHT_EDITOR,
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
        return int(getattr(value, "value", value))
    except Exception:
        return default


def _as_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default


def install_lighting_hooks():
    try:
        from server_commands import lighting_commands
    except Exception:
        return False

    ok = False

    show_fn = getattr(lighting_commands, "show_light_editor", None)
    if show_fn is not None:

        @Override(show_fn, role=Role.JOINER)
        def _show_light_editor_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                light_object_id = _as_int(
                    args[0] if args else kwargs.get("light_object_id")
                )
                light_target_type = _as_int(
                    args[1] if len(args) > 1 else kwargs.get("light_target_type")
                )
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SHOW_LIGHT_EDITOR,
                {
                    "light_object_id": light_object_id,
                    "light_target_type": light_target_type,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    set_fn = getattr(lighting_commands, "set_color_and_intensity", None)
    if set_fn is not None:

        @Override(set_fn, role=Role.JOINER)
        def _set_color_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                response_id = _as_int(args[0] if args else kwargs.get("response_id"))
                r = _as_int(args[1] if len(args) > 1 else kwargs.get("r"))
                g = _as_int(args[2] if len(args) > 2 else kwargs.get("g"))
                b = _as_int(args[3] if len(args) > 3 else kwargs.get("b"))
                intensity = _as_float(
                    args[4] if len(args) > 4 else kwargs.get("intensity"), 1.0
                )
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SET_COLOR_AND_INTENSITY,
                {
                    "response_id": response_id,
                    "r": r,
                    "g": g,
                    "b": b,
                    "intensity": intensity,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return True

        ok = True

    return ok


@MessageHandler(KIND_SHOW_LIGHT_EDITOR)
def _host_show_light_editor(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from server_commands import lighting_commands

        lighting_commands.show_light_editor(
            int(body.get("light_object_id") or 0),
            int(body.get("light_target_type") or 0),
        )
    except Exception:
        return


@MessageHandler(KIND_SET_COLOR_AND_INTENSITY)
def _host_set_color_and_intensity(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    response_id = int(body.get("response_id") or 0)
    dialog = deep_dialogs.get_dialog(response_id)
    if dialog is None:
        return
    try:
        import sims4.color

        color = sims4.color.from_rgba_as_int(
            int(body.get("r") or 0),
            int(body.get("g") or 0),
            int(body.get("b") or 0),
        )
        intensity = float(body.get("intensity") or 0.0)
        if hasattr(dialog, "update_dialog_data"):
            try:
                dialog.update_dialog_data(color=color, slider_value=intensity)
            except TypeError:
                dialog.update_dialog_data(color, intensity)
    except Exception:
        return
