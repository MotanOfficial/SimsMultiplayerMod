"""Zone-modifier (lot traits) delta sync from joiner unlock."""

from __future__ import division

from simmp.deep import KIND_ZONE_MODIFIERS_UPDATE, WrapperMessage
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


def _modifier_ids(mod_set):
    out = []
    for item in mod_set or []:
        try:
            out.append(int(getattr(item, "guid64", getattr(item, "id", item))))
        except Exception:
            continue
    return out


def install_zone_modifier_hooks():
    try:
        from services.persistence_service import PersistenceService
    except Exception:
        return False

    fn = getattr(PersistenceService, "set_read_write_lock", None)
    if fn is None:
        return False

    @Override(fn, role=Role.JOINER)
    def _lock_joiner(original, self, is_locked, *args, **kwargs):
        if not SESSION.enabled or SESSION.is_host:
            return original(self, is_locked, *args, **kwargs)
        # Only sync when unlocking (joiner finished a build/buy-style edit).
        if is_locked:
            return original(self, is_locked, *args, **kwargs)
        try:
            import services

            zms = services.get_zone_modifier_service()
            zone_id = services.current_zone_id()
            before = set(_modifier_ids(zms.get_zone_modifiers(zone_id, force_cache=True)))
            result = original(self, is_locked, *args, **kwargs)
            after = set(_modifier_ids(zms.get_zone_modifiers(zone_id, force_refresh=True)))
            removed = sorted(before - after)
            added = sorted(after - before)
            if removed or added:
                _relay_to_host(
                    KIND_ZONE_MODIFIERS_UPDATE,
                    {
                        "removed_modifiers": removed,
                        "added_modifiers": added,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
            return result
        except Exception:
            return original(self, is_locked, *args, **kwargs)

    return True


@MessageHandler(KIND_ZONE_MODIFIERS_UPDATE)
def _host_zone_modifiers_update(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services

        zone_id = services.current_zone_id()
        zone_data = services.get_persistence_service().get_zone_proto_buff(zone_id)
        if zone_data is None:
            return
        traits = list(getattr(zone_data, "lot_traits", []) or [])
        for mid in body.get("removed_modifiers") or []:
            mid = int(mid)
            if mid in traits:
                traits.remove(mid)
        for mid in body.get("added_modifiers") or []:
            mid = int(mid)
            if mid not in traits:
                traits.append(mid)
        # Prefer mutate-in-place when protobuf repeated field supports it.
        try:
            del zone_data.lot_traits[:]
            zone_data.lot_traits.extend(traits)
        except Exception:
            try:
                zone_data.lot_traits[:] = traits
            except Exception:
                pass
        zms = services.get_zone_modifier_service()
        if zms is not None and hasattr(zms, "check_for_and_apply_new_zone_modifiers"):
            zms.check_for_and_apply_new_zone_modifiers(zone_id)
    except Exception:
        return
