"""Disconnect multiplayer before a joiner save that allows shutdown.

When PersistenceService.save_using runs on a joiner and the service manager
allows shutdown (full save / exit path), tear down the deep session and the
network client so the save does not leave a half-live multiplayer connection.
"""

from __future__ import division

from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION

# Optional disconnect callback (connectivity binds this when available).
_disconnect_fn = None


def set_disconnect_fn(fn):
    """Register a callable used to drop the multiplayer connection on save."""
    global _disconnect_fn
    _disconnect_fn = fn


def _try_disconnect():
    if _disconnect_fn is not None:
        try:
            _disconnect_fn()
            return
        except Exception:
            pass
    try:
        from simmp_client.commands.cheat_commands import get_client

        client = get_client()
        if client is not None and hasattr(client, "disconnect"):
            client.disconnect()
            return
    except Exception:
        pass
    try:
        SESSION.deactivate()
    except Exception:
        pass


def install_persistence_hooks():
    try:
        from services.persistence_service import PersistenceService
    except Exception:
        return False

    fn = getattr(PersistenceService, "save_using", None)
    if fn is None:
        return False

    @Override(
        fn,
        role=Role.JOINER,
        target=PersistenceService,
        name="save_using",
        enabled_while_traveling=True,
    )
    def _save_using_joiner(original, self, *args, **kwargs):
        if SESSION.enabled and not SESSION.is_host:
            try:
                import game_services

                allow = bool(getattr(game_services.service_manager, "allow_shutdown", False))
            except Exception:
                allow = False
            if allow:
                _try_disconnect()
        return original(self, *args, **kwargs)

    return True
