"""Notebook generate / save-notes relays."""

from __future__ import division

from simmp.deep import KIND_GENERATE_NOTEBOOK, KIND_SAVE_NOTES, WrapperMessage
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


def install_notebook_hooks():
    try:
        from notebook import notebook_commands
    except Exception:
        return False

    ok = False

    gen_fn = getattr(notebook_commands, "generate_notebook", None)
    if gen_fn is not None:

        @Override(gen_fn, role=Role.JOINER)
        def _generate_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                opt_sim = args[0] if args else kwargs.get("opt_sim")
                cat = args[1] if len(args) > 1 else kwargs.get("initial_category")
                sub = args[2] if len(args) > 2 else kwargs.get("initial_subcategory")
                sim_id = _as_int(opt_sim) if opt_sim is not None else 0
                if not sim_id:
                    import services
                    active = services.active_sim_info()
                    sim_id = int(active.id) if active is not None else 0
                cat_i = -1 if cat is None else _as_int(cat, -1)
                sub_i = -1 if sub is None else _as_int(sub, -1)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_GENERATE_NOTEBOOK,
                {
                    "sim_id": sim_id,
                    "initial_category": cat_i,
                    "initial_subcategory": sub_i,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    save_fn = getattr(notebook_commands, "save_notes", None)
    if save_fn is not None:

        @Override(save_fn, role=Role.JOINER)
        def _save_notes_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                sim_id = _as_int(args[0] if args else kwargs.get("sim_id"))
                text = args[1] if len(args) > 1 else kwargs.get("text")
                text_s = str(text) if text is not None else ""
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SAVE_NOTES,
                {
                    "sim_id": sim_id,
                    "text": text_s,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


@MessageHandler(KIND_GENERATE_NOTEBOOK)
def _host_generate_notebook(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from notebook import notebook_commands

        sim_id = int(body.get("sim_id") or 0)
        cat = int(body.get("initial_category") if body.get("initial_category") is not None else -1)
        sub = int(body.get("initial_subcategory") if body.get("initial_subcategory") is not None else -1)
        notebook_commands.generate_notebook(
            sim_id if sim_id else None,
            None if cat < 0 else cat,
            None if sub < 0 else sub,
        )
    except Exception:
        return


@MessageHandler(KIND_SAVE_NOTES)
def _host_save_notes(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from notebook import notebook_commands

        notebook_commands.save_notes(int(body.get("sim_id") or 0), body.get("text") or "")
    except Exception:
        return
