"""Photo list relay (exit photo mode / submit captures)."""

from __future__ import division

import json

from simmp.deep import KIND_GET_PHOTO_LIST, WrapperMessage
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


def install_photo_hooks():
    try:
        from server_commands import photo_commands
    except Exception:
        return False

    fn = getattr(photo_commands, "get_photo_list", None)
    if fn is None:
        return False

    @Override(fn, role=Role.JOINER)
    def _get_photo_list_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            # Command signature is typically (*photo_list, _connection=...)
            photos = []
            for arg in args:
                if arg is None:
                    continue
                if isinstance(arg, (list, tuple)):
                    photos.extend(str(x) for x in arg)
                else:
                    photos.append(str(arg))
            if "photo_list" in kwargs and kwargs["photo_list"] is not None:
                pl = kwargs["photo_list"]
                if isinstance(pl, (list, tuple)):
                    photos.extend(str(x) for x in pl)
                else:
                    photos.append(str(pl))
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_GET_PHOTO_LIST,
            {
                "photo_list_json": json.dumps(photos),
                "player_id": int(SESSION.player_id or 0),
            },
        )
        return None

    return True


@MessageHandler(KIND_GET_PHOTO_LIST)
def _host_get_photo_list(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import json as _json
        from server_commands import photo_commands

        photos = _json.loads(body.get("photo_list_json") or "[]")
        if not isinstance(photos, list):
            photos = []
        fn = getattr(photo_commands, "get_photo_list", None)
        if fn is None:
            return
        # Replay with unpacked photo ids/strings when possible.
        try:
            fn(*photos)
        except TypeError:
            fn(photos)
    except Exception:
        return
