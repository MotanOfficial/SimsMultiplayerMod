"""Per-player selected-sim autonomy flags, applied on the host."""

from simmp.deep import KIND_SET_AUTONOMY_ENABLED, WrapperMessage
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.session import SESSION

# player_id -> whether selected-sim autonomy is enabled
selected_sim_autonomy_settings = {}


def apply_for_player(player_id, previous_sim=None):
    """Apply LIMITED_ONLY / UNDEFINED based on the player's autonomy toggle."""
    enabled = selected_sim_autonomy_settings.get(int(player_id), True)
    try:
        from autonomy.settings import AutonomyState
        from simmp_client.deep import sim_select
    except Exception:
        return
    active = sim_select.get_active_sim_for_player(player_id)
    if enabled:
        return
    if previous_sim is not None:
        try:
            previous_sim.autonomy_settings.set_setting(
                AutonomyState.UNDEFINED,
                previous_sim.get_autonomy_settings_group(),
            )
        except Exception:
            pass
    if active is not None:
        try:
            active.autonomy_settings.set_setting(
                AutonomyState.LIMITED_ONLY,
                active.get_autonomy_settings_group(),
            )
        except Exception:
            pass


def install_autonomy_hooks():
    try:
        from server_commands import autonomy_commands
    except Exception:
        return False

    fn = getattr(autonomy_commands, "set_autonomy_for_active_sim_option", None)
    if fn is None:
        return False

    from simmp_client.deep.override import Override, Role

    @Override(fn, role=Role.JOINER)
    def _set_autonomy_joiner(original, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(*args, **kwargs)
        enabled = True
        try:
            raw = args[0] if args else kwargs.get("enabled")
            enabled = bool(raw == "1" or raw is True or raw == 1)
        except Exception:
            pass
        wrapper = WrapperMessage(
            target_client=int(SESSION.host_player_id or 0),
            kind=KIND_SET_AUTONOMY_ENABLED,
            body={
                "enabled": enabled,
                "player_id": int(SESSION.player_id or 0),
            },
        )
        SESSION.send_wrapper(wrapper, route="host")
        return None

    return True


@MessageHandler(KIND_SET_AUTONOMY_ENABLED)
def _host_set_autonomy(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    player_id = int(body.get("player_id") or 0)
    enabled = bool(body.get("enabled"))
    if not player_id:
        return
    if selected_sim_autonomy_settings.get(player_id) == enabled:
        return
    selected_sim_autonomy_settings[player_id] = enabled
    try:
        from autonomy.settings import AutonomyState
        from simmp_client.deep import sim_select
    except Exception:
        return
    active = sim_select.get_active_sim_for_player(player_id)
    if active is None:
        return
    try:
        if enabled:
            active.autonomy_settings.set_setting(
                AutonomyState.UNDEFINED,
                active.get_autonomy_settings_group(),
            )
        else:
            active.autonomy_settings.set_setting(
                AutonomyState.LIMITED_ONLY,
                active.get_autonomy_settings_group(),
            )
    except Exception:
        return
