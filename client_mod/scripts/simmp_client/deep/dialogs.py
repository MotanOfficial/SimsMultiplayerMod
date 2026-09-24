"""Dialog response relays (joiner UI -> host UiDialog).

Joiners see dialog UI via GameNetworkMessage fan-out from Client.send_message.
Their ui.dialog.* commands never touch a local UiDialog; they relay intent to
the host, which owns active_dialogs and calls respond / pick_results /
on_text_input.
"""

from __future__ import division

import json

from simmp.deep import (
    KIND_DIALOG_PICK_RESULT,
    KIND_DIALOG_RESPONSE,
    KIND_DIALOG_TEXT_INPUT,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION

# dialog_id -> UiDialog instance (host only)
active_dialogs = {}

# Remember last dialog owner player for ambiguous NPC dialogs.
_last_target_player_id = None

# While applying a joiner response, tag the requesting player for interaction
# callbacks that resolve ownership (mirrors waiting_for_callback_player_id).
waiting_for_callback_player_id = None


def get_dialog(dialog_id):
    dialog_id = int(dialog_id)
    dialog = active_dialogs.get(dialog_id)
    if dialog is not None:
        return dialog
    try:
        import services

        zone = services.current_zone()
        if zone is None:
            return None
        svc = getattr(zone, "ui_dialog_service", None)
        if svc is None:
            svc = services.ui_dialog_service()
        if svc is None:
            return None
        return svc.get_dialog(dialog_id)
    except Exception:
        return None


def register_dialog(dialog):
    if dialog is None:
        return
    try:
        active_dialogs[int(dialog.dialog_id)] = dialog
    except Exception:
        return


def unregister_dialog(dialog_id):
    try:
        active_dialogs.pop(int(dialog_id), None)
    except Exception:
        return


def _target_player_id_for_dialog(dialog):
    """Resolve which joiner owns a dialog (owner sim -> active_sims map)."""
    global _last_target_player_id
    player_id = waiting_for_callback_player_id
    try:
        from simmp_client.deep import sim_select
    except Exception:
        sim_select = None

    if player_id is None and dialog is not None and sim_select is not None:
        owner = getattr(dialog, "owner", None)
        if owner is not None:
            player_id = sim_select.get_player_id_by_sim_id(int(owner.id))
            if player_id is None:
                parent = getattr(owner, "parent", None)
                if parent is not None:
                    player_id = sim_select.get_player_id_by_sim_id(int(parent.id))
            if player_id is None:
                # Non-human / orphaned: reuse last known target.
                is_human = getattr(owner, "is_human", True)
                if not is_human:
                    player_id = _last_target_player_id
    if player_id is not None:
        _last_target_player_id = int(player_id)
    return player_id


def _send_dialog_close(dialog_id, player_id):
    if not player_id or player_id == SESSION.player_id:
        return
    try:
        from protocolbuffers import Consts_pb2, Dialog_pb2
        from simmp_client.deep.game_network import send_message_over_network

        close = Dialog_pb2.UiDialogCloseRequest()
        close.dialog_id = int(dialog_id)
        msg_id = getattr(Consts_pb2, "MSG_UI_DIALOG_CLOSE", None)
        if msg_id is None:
            return
        send_message_over_network(msg_id, close, int(player_id))
    except Exception:
        return


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


def install_dialog_hooks():
    """Patch ui_commands (joiner) and UiDialogService.dialog_show (host)."""
    ok = False
    try:
        from server_commands import ui_commands
    except Exception:
        ui_commands = None

    if ui_commands is not None:
        respond_fn = getattr(ui_commands, "ui_dialog_respond", None)
        if respond_fn is not None:

            @Override(respond_fn, role=Role.JOINER)
            def _ui_dialog_respond_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    dialog_id = int(args[0])
                    response = int(args[1])
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_DIALOG_RESPONSE,
                    {
                        "dialog_id": dialog_id,
                        "response": response,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        pick_fn = getattr(ui_commands, "ui_dialog_pick_result", None)
        if pick_fn is not None:

            @Override(pick_fn, role=Role.JOINER)
            def _ui_dialog_pick_result_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    dialog_id = int(args[0])
                    ingredient_check = _as_bool_flag(args[1]) if len(args) > 1 else False
                    prepped = _as_bool_flag(args[2]) if len(args) > 2 else False
                    choices = []
                    for i in range(3, len(args)):
                        try:
                            choices.append(int(args[i]))
                        except Exception:
                            break
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_DIALOG_PICK_RESULT,
                    {
                        "dialog_id": dialog_id,
                        "ingredient_check": ingredient_check,
                        "prepped_ingredient_check": prepped,
                        "choices_json": json.dumps(choices),
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        text_fn = getattr(ui_commands, "ui_dialog_text_input", None)
        if text_fn is not None:

            @Override(text_fn, role=Role.JOINER)
            def _ui_dialog_text_input_joiner(original, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host:
                    return original(*args, **kwargs)
                try:
                    dialog_id = int(kwargs.get("dialog_id", args[0] if args else 0))
                    name = kwargs.get("text_input_name")
                    value = kwargs.get("text_input_value")
                    if name is None and len(args) > 1:
                        name = args[1]
                    if value is None and len(args) > 2:
                        value = args[2]
                except Exception:
                    return original(*args, **kwargs)
                _relay_to_host(
                    KIND_DIALOG_TEXT_INPUT,
                    {
                        "dialog_id": int(dialog_id),
                        "text_input_name": str(name or ""),
                        "text_input_value": str(value or ""),
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

    try:
        from ui.ui_dialog_service import UiDialogService
    except Exception:
        return ok

    show_fn = getattr(UiDialogService, "dialog_show", None)
    if show_fn is None:
        return ok

    @Override(show_fn, role=Role.HOST, target=UiDialogService, name="dialog_show")
    def _dialog_show_host(original, self, dialog, *args, **kwargs):
        result = original(self, dialog, *args, **kwargs)
        if not SESSION.enabled or not SESSION.is_host:
            return result
        if dialog is None:
            return result
        register_dialog(dialog)
        # Resolve ownership so interaction callbacks can attribute replies.
        _target_player_id_for_dialog(dialog)
        return result

    return True


@MessageHandler(KIND_DIALOG_RESPONSE)
def _host_dialog_response(wrapper):
    global waiting_for_callback_player_id
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    dialog_id = int(body.get("dialog_id") or 0)
    response = int(body.get("response") or 0)
    player_id = int(body.get("player_id") or 0)
    if not dialog_id:
        return
    waiting_for_callback_player_id = player_id or None
    try:
        dialog = active_dialogs.pop(dialog_id, None)
        if dialog is None:
            dialog = get_dialog(dialog_id)
        if dialog is None:
            return
        try:
            dialog.respond(response)
        except Exception:
            pass
        # Always try to close joiner UI so stuck modals clear.
        _send_dialog_close(dialog_id, player_id)
        unregister_dialog(dialog_id)
    finally:
        waiting_for_callback_player_id = None


@MessageHandler(KIND_DIALOG_PICK_RESULT)
def _host_dialog_pick_result(wrapper):
    global waiting_for_callback_player_id
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    dialog_id = int(body.get("dialog_id") or 0)
    player_id = int(body.get("player_id") or 0)
    if not dialog_id:
        return
    try:
        choices = json.loads(body.get("choices_json") or "[]")
        if not isinstance(choices, list):
            choices = []
        choices = [int(c) for c in choices]
    except Exception:
        choices = []
    ingredient_check = bool(body.get("ingredient_check"))
    prepped = bool(body.get("prepped_ingredient_check"))
    waiting_for_callback_player_id = player_id or None
    try:
        dialog = get_dialog(dialog_id)
        if dialog is None:
            return
        try:
            dialog.pick_results(
                picked_results=choices,
                ingredient_check=ingredient_check,
                prepped_ingredient_check=prepped,
            )
        except TypeError:
            try:
                dialog.pick_results(choices, ingredient_check, prepped)
            except Exception:
                return
        except Exception:
            return
    finally:
        waiting_for_callback_player_id = None


@MessageHandler(KIND_DIALOG_TEXT_INPUT)
def _host_dialog_text_input(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    dialog_id = int(body.get("dialog_id") or 0)
    name = body.get("text_input_name") or ""
    value = body.get("text_input_value") or ""
    if not dialog_id:
        return
    dialog = get_dialog(dialog_id)
    if dialog is None:
        return
    try:
        dialog.on_text_input(name, value)
    except Exception:
        return