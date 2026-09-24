"""Lifestyle dialog + equip-trait relays."""

from __future__ import division

from simmp.deep import (
    KIND_EQUIP_TRAIT,
    KIND_GENERATE_LIFESTYLES_DIALOG,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION
from simmp_client.deep import dialogs as deep_dialogs
from simmp_client.deep import sim_select


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
        return int(getattr(value, "id", getattr(value, "guid64", getattr(value, "value", value))))
    except Exception:
        return default


def install_trait_hooks():
    try:
        from traits import trait_commands
    except Exception:
        return False

    ok = False

    life_fn = getattr(trait_commands, "generate_lifestyles_dialog_ui", None)
    if life_fn is not None:

        @Override(life_fn, role=Role.JOINER)
        def _lifestyles_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                # Signature: (lifestyle_dialog_id, sim) — we only need sim.
                sim = args[1] if len(args) > 1 else kwargs.get("sim")
                if sim is None and args:
                    sim = args[0]
                sim_id = _as_int(sim)
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_GENERATE_LIFESTYLES_DIALOG,
                {
                    "sim_id": sim_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    equip_fn = getattr(trait_commands, "equip_trait", None)
    if equip_fn is not None:

        @Override(equip_fn, role=Role.JOINER)
        def _equip_trait_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                trait_type = _as_int(args[0] if args else kwargs.get("trait_type"))
                opt_sim = _as_int(args[1] if len(args) > 1 else kwargs.get("opt_sim"))
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_EQUIP_TRAIT,
                {
                    "trait_type": trait_type,
                    "sim_id": opt_sim,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


@MessageHandler(KIND_GENERATE_LIFESTYLES_DIALOG)
def _host_generate_lifestyles_dialog(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    prev = deep_dialogs.waiting_for_callback_player_id
    deep_dialogs.waiting_for_callback_player_id = player_id or None
    try:
        from traits import trait_commands

        sim_id = int(body.get("sim_id") or 0)
        # Replay original so dialog fans via GameNetwork.
        try:
            trait_commands.generate_lifestyles_dialog_ui(None, sim_id)
        except TypeError:
            trait_commands.generate_lifestyles_dialog_ui(sim_id)
    except Exception:
        return
    finally:
        deep_dialogs.waiting_for_callback_player_id = prev


@MessageHandler(KIND_EQUIP_TRAIT)
def _host_equip_trait(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services
        from sims4.resources import Types

        sim_id = int(body.get("sim_id") or 0)
        info = services.sim_info_manager().get(sim_id) if sim_id else None
        if info is None:
            player_id = int(body.get("player_id") or 0)
            info = sim_select.get_active_sim_for_player(player_id)
        if info is None:
            return
        trait_id = int(body.get("trait_type") or 0)
        trait = services.get_instance_manager(Types.TRAIT).get(trait_id)
        if trait is None:
            return
        target = getattr(info, "sim_info", info)
        target.add_trait(trait)
        if hasattr(target, "resend_trait_ids"):
            try:
                target.resend_trait_ids(trait.guid64)
            except Exception:
                target.resend_trait_ids()
    except Exception:
        return
