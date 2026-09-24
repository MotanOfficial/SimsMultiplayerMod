"""Street civic policy / community board relays."""

from __future__ import division

from simmp.deep import (
    KIND_HANDLE_COMMUNITY_BOARD,
    KIND_SHOW_COMMUNITY_BOARD,
    KIND_STREET_CIVIC_REQUEST_ADD_PICKER,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION


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


def install_civic_policy_hooks():
    try:
        from civic_policies import street_civic_policy_commands
    except Exception:
        try:
            from server_commands import street_civic_policy_commands
        except Exception:
            return False

    ok = False

    picker_fn = getattr(street_civic_policy_commands, "street_civic_policy_request_add_picker", None)
    if picker_fn is not None:

        @Override(picker_fn, role=Role.JOINER)
        def _picker_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                opt_target = args[0] if args else kwargs.get("opt_target")
                if opt_target is None:
                    opt_id = -1
                else:
                    opt_id = _as_int(opt_target, -1)
                added = args[1] if len(args) > 1 else kwargs.get("added_policies_string", "")
                added = "" if added is None else str(added)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_STREET_CIVIC_REQUEST_ADD_PICKER,
                {
                    "opt_target_id": opt_id,
                    "added_policies_string": added,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    board_fn = getattr(street_civic_policy_commands, "handle_community_board", None)
    if board_fn is not None:

        @Override(board_fn, role=Role.JOINER)
        def _board_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                resp = args[0] if args else kwargs.get("community_board_response")
                resp = "" if resp is None else str(resp)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_HANDLE_COMMUNITY_BOARD,
                {
                    "community_board_response": resp,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    show_fn = getattr(street_civic_policy_commands, "street_civic_policy_show_community_board", None)
    if show_fn is not None:

        @Override(show_fn, role=Role.JOINER)
        def _show_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                current_street = _as_bool(
                    args[0] if args else kwargs.get("current_street", True)
                )
                opt_sim = _as_int(args[1] if len(args) > 1 else kwargs.get("opt_sim"))
                opt_target = _as_int(
                    args[2] if len(args) > 2 else kwargs.get("opt_target_id")
                )
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SHOW_COMMUNITY_BOARD,
                {
                    "current_street": current_street,
                    "opt_sim": opt_sim,
                    "opt_target_id": opt_target,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


@MessageHandler(KIND_STREET_CIVIC_REQUEST_ADD_PICKER)
def _host_request_add_picker(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        try:
            from civic_policies import street_civic_policy_commands
        except Exception:
            from server_commands import street_civic_policy_commands

        opt = body.get("opt_target_id", -1)
        if opt is None or int(opt) == -1:
            opt_arg = None
        else:
            opt_arg = int(opt)
        street_civic_policy_commands.street_civic_policy_request_add_picker(
            opt_arg,
            body.get("added_policies_string") or "",
        )
    except Exception:
        return


@MessageHandler(KIND_HANDLE_COMMUNITY_BOARD)
def _host_handle_community_board(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        try:
            from civic_policies import street_civic_policy_commands
        except Exception:
            from server_commands import street_civic_policy_commands

        street_civic_policy_commands.handle_community_board(
            body.get("community_board_response") or "",
        )
    except Exception:
        return


@MessageHandler(KIND_SHOW_COMMUNITY_BOARD)
def _host_show_community_board(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        try:
            from civic_policies import street_civic_policy_commands
        except Exception:
            from server_commands import street_civic_policy_commands

        street_civic_policy_commands.street_civic_policy_show_community_board(
            bool(body.get("current_street", True)),
            int(body.get("opt_sim") or 0),
            int(body.get("opt_target_id") or 0),
        )
    except Exception:
        return
