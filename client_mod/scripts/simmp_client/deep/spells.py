"""Spellbook UI generate relay."""

from __future__ import division

from simmp.deep import KIND_GENERATE_SPELLBOOK_UI, WrapperMessage
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


def install_spell_hooks():
    try:
        from spells import spell_commands
    except Exception:
        return False

    fn = getattr(spell_commands, "generate_spell_book_ui", None)
    if fn is None:
        return False

    @Override(fn, role=Role.JOINER)
    def _spellbook_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        try:
            opt_target = _as_int(args[0] if args else kwargs.get("opt_target"))
            context = args[1] if len(args) > 1 else kwargs.get("context")
            ctx_s = str(context) if context is not None else ""
        except Exception:
            return original(*args, **kwargs)
        _relay_to_host(
            KIND_GENERATE_SPELLBOOK_UI,
            {
                "opt_target_id": opt_target,
                "context": ctx_s,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        return None

    return True


@MessageHandler(KIND_GENERATE_SPELLBOOK_UI)
def _host_generate_spellbook(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from spells import spell_commands

        opt = int(body.get("opt_target_id") or 0)
        ctx = body.get("context") or None
        if ctx == "":
            ctx = None
        spell_commands.generate_spell_book_ui(opt, ctx)
    except Exception:
        return
