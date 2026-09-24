"""Build/buy C-API extras beyond create/destroy/location."""

from __future__ import division

from simmp.deep import (
    KIND_BUILD_BUY_EXIT,
    KIND_CLEAR_PARENT_OBJECT,
    KIND_RESET_OBJECT,
    KIND_SCALE_OBJECT,
    KIND_SET_BUILD_BUY_FLAGS,
    KIND_SET_DEFINITION,
    KIND_SET_FLOOR_FEATURE,
    KIND_SET_PARENT_OBJECT,
    WrapperMessage,
)
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION

_applying = False


def _relay_to_host(kind, body):
    wrapper = WrapperMessage(
        target_client=int(SESSION.host_player_id or 0),
        kind=kind,
        body=body,
    )
    return SESSION.send_wrapper(wrapper, route="host")


def _broadcast(kind, body):
    wrapper = WrapperMessage(kind=kind, body=body)
    return SESSION.send_wrapper(wrapper, route="broadcast")


def _as_int(value, default=0):
    if value is None:
        return default
    try:
        return int(getattr(value, "id", getattr(value, "value", value)))
    except Exception:
        return default


def _pickle_transform(transform):
    try:
        import json
        # Prefer a plain dict if Transform exposes components.
        if hasattr(transform, "translation") and hasattr(transform, "orientation"):
            t = transform.translation
            o = transform.orientation
            payload = {
                "tx": float(getattr(t, "x", 0.0)),
                "ty": float(getattr(t, "y", 0.0)),
                "tz": float(getattr(t, "z", 0.0)),
                "ox": float(getattr(o, "x", 0.0)),
                "oy": float(getattr(o, "y", 0.0)),
                "oz": float(getattr(o, "z", 0.0)),
                "ow": float(getattr(o, "w", 1.0)),
            }
            return json.dumps(payload).encode("utf-8")
        return repr(transform).encode("utf-8")
    except Exception:
        return b""


def _unpickle_transform(raw):
    if not raw:
        return None
    try:
        import json
        import sims4.math
        data = json.loads(raw.decode("utf-8"))
        translation = sims4.math.Vector3(data["tx"], data["ty"], data["tz"])
        orientation = sims4.math.Quaternion(data["ox"], data["oy"], data["oz"], data["ow"])
        return sims4.math.Transform(translation, orientation)
    except Exception:
        return None


def install_buy_hooks():
    ok = False
    try:
        from objects import system
    except Exception:
        system = None
    try:
        import build_buy
    except Exception:
        build_buy = None

    if system is not None:
        clear_fn = getattr(system, "c_api_clear_parent_object", None)
        if clear_fn is not None:

            @Override(clear_fn, role=Role.JOINER)
            def _clear_parent_joiner(original, obj_id, transform, zone_id, surface, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host or _applying:
                    return original(obj_id, transform, zone_id, surface, *args, **kwargs)
                try:
                    sec = int(getattr(surface, "secondary_id", 0) or 0)
                    stype = int(getattr(surface, "type", 0) or 0)
                except Exception:
                    sec, stype = 0, 0
                _relay_to_host(
                    KIND_CLEAR_PARENT_OBJECT,
                    {
                        "obj_id": _as_int(obj_id),
                        "transform": _pickle_transform(transform),
                        "routing_surface_secondary_id": sec,
                        "routing_surface_type": stype,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        flags_fn = getattr(system, "c_api_set_buildbuy_use_flags", None)
        if flags_fn is not None:

            @Override(flags_fn, role=Role.JOINER)
            def _flags_joiner(original, zone_id, object_id, build_buy_use_flags, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host or _applying:
                    return original(zone_id, object_id, build_buy_use_flags, *args, **kwargs)
                _relay_to_host(
                    KIND_SET_BUILD_BUY_FLAGS,
                    {
                        "zone_id": _as_int(zone_id),
                        "object_id": _as_int(object_id),
                        "build_buy_use_flags": _as_int(build_buy_use_flags),
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        reset_fn = getattr(system, "c_api_reset_object", None)
        if reset_fn is not None:

            @Override(reset_fn, role=Role.JOINER)
            def _reset_joiner(original, zone_id, obj_or_id, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host or _applying:
                    return original(zone_id, obj_or_id, *args, **kwargs)
                _relay_to_host(
                    KIND_RESET_OBJECT,
                    {
                        "zone_id": _as_int(zone_id),
                        "obj_id": _as_int(obj_or_id),
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        parent_fn = getattr(system, "c_api_set_parent_object", None)
        if parent_fn is not None:

            @Override(parent_fn, role=Role.JOINER)
            def _set_parent_joiner(original, obj_id, parent_id, transform, joint_name=None, slot_hash=0, zone_id=None, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host or _applying:
                    return original(obj_id, parent_id, transform, joint_name, slot_hash, zone_id, *args, **kwargs)
                _relay_to_host(
                    KIND_SET_PARENT_OBJECT,
                    {
                        "obj_id": _as_int(obj_id),
                        "parent_id": _as_int(parent_id),
                        "transform": _pickle_transform(transform),
                        "joint_name": "" if joint_name is None else str(joint_name),
                        "slot_hash": _as_int(slot_hash),
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

    try:
        from objects.client_object_mixin import ClientObjectMixin
    except Exception:
        ClientObjectMixin = None

    if ClientObjectMixin is not None:
        def_fn = getattr(ClientObjectMixin, "set_definition", None)
        if def_fn is not None:

            @Override(def_fn, role=Role.JOINER)
            def _set_def_joiner(original, self, definition_id, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host or _applying:
                    return original(self, definition_id, *args, **kwargs)
                _relay_to_host(
                    KIND_SET_DEFINITION,
                    {
                        "obj_id": _as_int(getattr(self, "id", 0)),
                        "definition_id": _as_int(definition_id),
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return None

            ok = True

        scale_fn = getattr(ClientObjectMixin, "_resend_client_scale", None)
        if scale_fn is not None:

            @Override(scale_fn, role=Role.JOINER)
            def _scale_joiner(original, self, *args, **kwargs):
                if not SESSION.enabled or SESSION.is_host or _applying:
                    return original(self, *args, **kwargs)
                try:
                    scale = float(getattr(self, "scale", 1.0))
                except Exception:
                    scale = 1.0
                _relay_to_host(
                    KIND_SCALE_OBJECT,
                    {
                        "obj_id": _as_int(getattr(self, "id", 0)),
                        "scale": scale,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
                return original(self, *args, **kwargs)

            ok = True

    if build_buy is not None:
        # Joiner build/buy exit notifies host so navmesh/callbacks run authoritatively.
        try:
            def _on_build_buy_exit():
                if not SESSION.enabled or SESSION.is_host:
                    return
                _relay_to_host(
                    KIND_BUILD_BUY_EXIT,
                    {"player_id": int(SESSION.player_id or 0)},
                )

            if hasattr(build_buy, "register_build_buy_exit_callback"):
                build_buy.register_build_buy_exit_callback(_on_build_buy_exit)
                ok = True
        except Exception:
            pass

    return ok


@MessageHandler(KIND_CLEAR_PARENT_OBJECT)
def _host_clear_parent(wrapper):
    global _applying
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import routing
        import services
        from objects import system

        transform = _unpickle_transform(body.get("transform") or b"")
        surface = routing.SurfaceIdentifier(
            services.current_zone_id(),
            int(body.get("routing_surface_secondary_id") or 0),
            int(body.get("routing_surface_type") or 0),
        )
        obj = system.find_object(int(body.get("obj_id") or 0))
        if obj is None:
            return
        _applying = True
        try:
            try:
                obj.build_buy_use_flags = 0
            except Exception:
                pass
            if transform is not None:
                obj.clear_parent(transform, surface)
            system.reset_object(int(body.get("obj_id") or 0), True, "Build/Buy")
        finally:
            _applying = False
    except Exception:
        _applying = False


@MessageHandler(KIND_SET_BUILD_BUY_FLAGS)
def _host_set_flags(wrapper):
    global _applying
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services

        zone = services.get_zone(int(body.get("zone_id") or 0))
        if zone is None:
            return
        obj = zone.find_object(int(body.get("object_id") or 0))
        if obj is None:
            return
        _applying = True
        try:
            obj.build_buy_use_flags = int(body.get("build_buy_use_flags") or 0)
        finally:
            _applying = False
    except Exception:
        _applying = False


@MessageHandler(KIND_RESET_OBJECT)
def _host_reset_object(wrapper):
    global _applying
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from objects import system

        _applying = True
        try:
            system.reset_object(int(body.get("zone_id") or 0), int(body.get("obj_id") or 0))
        except TypeError:
            system.reset_object(int(body.get("obj_id") or 0))
        finally:
            _applying = False
    except Exception:
        _applying = False


@MessageHandler(KIND_SET_PARENT_OBJECT)
def _host_set_parent(wrapper):
    global _applying
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from objects import system

        transform = _unpickle_transform(body.get("transform") or b"")
        joint = body.get("joint_name") or None
        if joint == "":
            joint = None
        _applying = True
        try:
            system.set_parent_object(
                int(body.get("obj_id") or 0),
                int(body.get("parent_id") or 0),
                transform,
                joint,
                int(body.get("slot_hash") or 0),
            )
        finally:
            _applying = False
    except Exception:
        _applying = False


@MessageHandler(KIND_SET_DEFINITION)
def _host_set_definition(wrapper):
    global _applying
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services

        obj = services.current_zone().find_object(int(body.get("obj_id") or 0))
        if obj is None:
            return
        _applying = True
        try:
            obj.set_definition(int(body.get("definition_id") or 0))
        finally:
            _applying = False
    except Exception:
        _applying = False


@MessageHandler(KIND_SCALE_OBJECT)
def _host_scale_object(wrapper):
    global _applying
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services

        obj = services.current_zone().find_object(int(body.get("obj_id") or 0))
        if obj is None:
            return
        _applying = True
        try:
            obj.scale = float(body.get("scale") or 1.0)
        finally:
            _applying = False
    except Exception:
        _applying = False


@MessageHandler(KIND_BUILD_BUY_EXIT)
def _host_build_buy_exit(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    try:
        import build_buy

        if hasattr(build_buy, "_build_buy_exit_callbacks"):
            build_buy._build_buy_exit_callbacks()
    except Exception:
        return


@MessageHandler(KIND_SET_FLOOR_FEATURE)
def _on_set_floor_feature(wrapper):
    """Joiners apply host-authored floor feature (dust/burn) overlays."""
    if not SESSION.enabled or SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import build_buy
        import services
        import sims4.math

        point = sims4.math.Vector3(
            float(body.get("point_x") or 0.0),
            float(body.get("point_y") or 0.0),
            float(body.get("point_z") or 0.0),
        )
        ftype = int(body.get("floor_feature_type") or 0)
        build_buy.set_floor_feature(
            services.current_zone_id(),
            ftype,
            point,
            int(body.get("level_index") or 0),
            float(body.get("value") or 0.0),
        )
    except Exception:
        return
