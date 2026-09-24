"""Build-buy object create / destroy / set-location deep relays.

Shared object IDs: the local side creates/moves/destroys immediately and
broadcasts the same IDs so peers keep one authoritative world graph without
jsonpickle.
"""

from simmp.deep import (
    KIND_CREATE_OBJECT,
    KIND_DESTROY_OBJECT,
    KIND_SET_OBJECT_LOCATION,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION

# Suppress re-entrant relay when applying a peer message locally.
_applying_remote = False


def _pack_transform(transform):
    out = {"tx": 0.0, "ty": 0.0, "tz": 0.0, "ox": 0.0, "oy": 0.0, "oz": 0.0, "ow": 1.0}
    if transform is None:
        return out
    try:
        t = getattr(transform, "translation", None)
        if t is not None:
            out["tx"] = float(getattr(t, "x", 0.0))
            out["ty"] = float(getattr(t, "y", 0.0))
            out["tz"] = float(getattr(t, "z", 0.0))
        o = getattr(transform, "orientation", None)
        if o is not None:
            out["ox"] = float(getattr(o, "x", 0.0))
            out["oy"] = float(getattr(o, "y", 0.0))
            out["oz"] = float(getattr(o, "z", 0.0))
            out["ow"] = float(getattr(o, "w", 1.0))
    except Exception:
        pass
    return out


def _make_transform(body):
    try:
        from sims4.math import Quaternion, Transform, Vector3

        return Transform(
            Vector3(body.get("tx", 0.0), body.get("ty", 0.0), body.get("tz", 0.0)),
            Quaternion(
                body.get("ox", 0.0),
                body.get("oy", 0.0),
                body.get("oz", 0.0),
                body.get("ow", 1.0),
            ),
        )
    except Exception:
        return None


def _broadcast(kind, body):
    if not SESSION.enabled or _applying_remote:
        return False
    wrapper = WrapperMessage(
        target_client=0,
        client_id=int(SESSION.player_id or 0),
        kind=kind,
        body=body,
    )
    return SESSION.send_wrapper(wrapper, route="broadcast")


def _generate_object_id():
    try:
        import id_generator

        return int(id_generator.generate_object_id())
    except Exception:
        import random

        return int(random.getrandbits(63))


def install_object_hooks():
    try:
        from objects import system
        import build_buy
    except Exception:
        return False

    create_fn = getattr(system, "c_api_create_object", None)
    destroy_fn = getattr(system, "c_api_destroy_object", None)
    set_loc_fn = getattr(build_buy, "c_api_set_object_location_ex", None)

    if create_fn is not None:

        @Override(create_fn, role=Role.ALL)
        def _c_api_create_object(original, zone_id, def_id, obj_id=None, obj_state=None, loc_type=None, content_source=None, *args, **kwargs):
            if not SESSION.enabled or _applying_remote:
                return original(zone_id, def_id, obj_id, obj_state, loc_type, content_source, *args, **kwargs)
            if not obj_id:
                obj_id = _generate_object_id()
            try:
                loc_i = int(getattr(loc_type, "value", loc_type) if loc_type is not None else 0)
            except Exception:
                loc_i = 0
            try:
                cs_i = int(getattr(content_source, "value", content_source) if content_source is not None else 0)
            except Exception:
                cs_i = 0
            _broadcast(
                KIND_CREATE_OBJECT,
                {
                    "def_id": int(def_id),
                    "obj_id": int(obj_id),
                    "loc_type": loc_i,
                    "zone_id": int(zone_id),
                    "content_source": cs_i,
                    "disable_object_commodity_callbacks": False,
                },
            )
            try:
                return original(zone_id, def_id, obj_id, obj_state, loc_type, content_source, *args, **kwargs)
            except TypeError:
                return original(zone_id, def_id, obj_id, obj_state, loc_type, content_source)

    if destroy_fn is not None:

        @Override(destroy_fn, role=Role.ALL)
        def _c_api_destroy_object(original, zone_id, obj_or_id, *args, **kwargs):
            if not SESSION.enabled or _applying_remote:
                return original(zone_id, obj_or_id, *args, **kwargs)
            try:
                obj_id = int(obj_or_id.id) if hasattr(obj_or_id, "id") else int(obj_or_id)
            except Exception:
                return original(zone_id, obj_or_id, *args, **kwargs)
            _broadcast(
                KIND_DESTROY_OBJECT,
                {"zone_id": int(zone_id), "obj_id": obj_id},
            )
            return original(zone_id, obj_or_id, *args, **kwargs)

    if set_loc_fn is not None:

        @Override(set_loc_fn, role=Role.ALL)
        def _c_api_set_object_location_ex(original, zone_id, obj_id, routing_surface, transform, parent_id=None, parent_type_info=None, slot_hash=None, *args, **kwargs):
            if not SESSION.enabled or _applying_remote:
                return original(zone_id, obj_id, routing_surface, transform, parent_id, parent_type_info, slot_hash, *args, **kwargs)
            packed = _pack_transform(transform)
            secondary = 0
            surface_type = 0
            try:
                secondary = int(getattr(routing_surface, "secondary_id", 0) or 0)
                surface_type = int(getattr(routing_surface, "type", 0) or 0)
            except Exception:
                pass
            p0 = 0
            p1 = 0
            try:
                if parent_type_info is not None:
                    p0 = int(parent_type_info[0])
                    p1 = int(parent_type_info[1])
            except Exception:
                pass
            body = {
                "zone_id": int(zone_id),
                "obj_id": int(obj_id),
                "parent_id": int(parent_id) if parent_id else 0,
                "slot_hash": int(slot_hash) if slot_hash else 0,
                "parent_type_info_0": p0,
                "parent_type_info_1": p1,
                "routing_surface_secondary_id": secondary,
                "routing_surface_type": surface_type,
            }
            body.update(packed)
            _broadcast(KIND_SET_OBJECT_LOCATION, body)
            return original(zone_id, obj_id, routing_surface, transform, parent_id, parent_type_info, slot_hash, *args, **kwargs)

    return True


@MessageHandler(KIND_CREATE_OBJECT)
def _on_create_object(wrapper):
    global _applying_remote
    if not SESSION.enabled or _applying_remote:
        return
    body = wrapper.body or {}
    # Skip echo of our own broadcast.
    if wrapper.client_id and SESSION.player_id and int(wrapper.client_id) == int(SESSION.player_id):
        return
    try:
        import services
        from objects import system
        from objects.gallery_tuning import ContentSource
        from objects.object_enums import ItemLocation
    except Exception:
        return
    obj_id = int(body.get("obj_id") or 0)
    def_id = int(body.get("def_id") or 0)
    zone_id = int(body.get("zone_id") or 0)
    if not obj_id or not def_id:
        return
    try:
        zone = services.get_zone(zone_id) if zone_id else services.current_zone()
        if zone is not None and zone.find_object(obj_id) is not None:
            return
    except Exception:
        pass
    loc_type = body.get("loc_type", 0)
    content_source = body.get("content_source", 0)
    try:
        loc_type = ItemLocation(loc_type)
    except Exception:
        pass
    try:
        content_source = ContentSource(content_source)
    except Exception:
        pass
    _applying_remote = True
    try:
        system.c_api_create_object(zone_id, def_id, obj_id, None, loc_type, content_source)
    except TypeError:
        try:
            system.c_api_create_object(zone_id, def_id, obj_id)
        except Exception:
            pass
    except Exception:
        pass
    finally:
        _applying_remote = False


@MessageHandler(KIND_DESTROY_OBJECT)
def _on_destroy_object(wrapper):
    global _applying_remote
    if not SESSION.enabled or _applying_remote:
        return
    if wrapper.client_id and SESSION.player_id and int(wrapper.client_id) == int(SESSION.player_id):
        return
    body = wrapper.body or {}
    obj_id = int(body.get("obj_id") or 0)
    zone_id = int(body.get("zone_id") or 0)
    if not obj_id:
        return
    _applying_remote = True
    try:
        from objects import system

        obj = None
        try:
            obj = system._get_obj_for_obj_or_id(obj_id)
        except Exception:
            try:
                import services

                zone = services.get_zone(zone_id) if zone_id else services.current_zone()
                obj = zone.find_object(obj_id) if zone is not None else None
            except Exception:
                obj = None
        if obj is not None:
            try:
                obj.destroy(obj, "Destruction request from deep relay.", source=obj, cause="Destruction request from deep relay.")
            except TypeError:
                try:
                    obj.destroy()
                except Exception:
                    pass
            except Exception:
                pass
        else:
            try:
                system.c_api_destroy_object(zone_id, obj_id)
            except Exception:
                pass
    finally:
        _applying_remote = False


@MessageHandler(KIND_SET_OBJECT_LOCATION)
def _on_set_object_location(wrapper):
    global _applying_remote
    if not SESSION.enabled or _applying_remote:
        return
    if wrapper.client_id and SESSION.player_id and int(wrapper.client_id) == int(SESSION.player_id):
        return
    body = wrapper.body or {}
    try:
        import routing
        import services
    except Exception:
        return
    zone_id = int(body.get("zone_id") or 0)
    obj_id = int(body.get("obj_id") or 0)
    try:
        zone = services.get_zone(zone_id) if zone_id else services.current_zone()
        obj = zone.find_object(obj_id) if zone is not None else None
    except Exception:
        obj = None
    if obj is None:
        return
    transform = _make_transform(body)
    try:
        surface = routing.SurfaceIdentifier(
            services.current_zone_id(),
            body.get("routing_surface_secondary_id", 0),
            body.get("routing_surface_type", 0),
        )
    except Exception:
        surface = None
    parent = None
    parent_id = int(body.get("parent_id") or 0)
    if parent_id:
        try:
            parent = services.object_manager().get(parent_id)
        except Exception:
            parent = None
    _applying_remote = True
    try:
        try:
            obj.parent_type_info = (
                body.get("parent_type_info_0", 0),
                body.get("parent_type_info_1", 0),
            )
        except Exception:
            pass
        try:
            obj.set_parent(
                parent,
                transform,
                slot_hash=body.get("slot_hash", 0),
                routing_surface=surface,
            )
        except TypeError:
            try:
                obj.set_parent(parent, transform, body.get("slot_hash", 0), surface)
            except Exception:
                if transform is not None:
                    try:
                        obj.set_location(transform)
                    except Exception:
                        pass
        try:
            obj.scale = obj.scale
        except Exception:
            pass
    finally:
        _applying_remote = False