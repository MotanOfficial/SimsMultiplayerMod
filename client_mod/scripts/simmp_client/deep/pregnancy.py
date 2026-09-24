"""Pregnancy create-sim-info fan-out (host -> joiners).

When the host pregnancy tracker materializes a new SimInfo, joiners receive
opaque SimData bytes and load a selectable mirror.
"""

from __future__ import division

from simmp.deep import KIND_CREATE_SIM_INFO, WrapperMessage
from simmp_client.deep.message_handler import MessageHandler
from simmp_client.deep.override import Override, Role
from simmp_client.deep.session import SESSION

_applying = False


def _broadcast(kind, body):
    wrapper = WrapperMessage(kind=kind, body=body)
    return SESSION.send_wrapper(wrapper, route="broadcast")


def install_pregnancy_hooks():
    try:
        from sims.pregnancy.pregnancy_tracker import PregnancyTracker
    except Exception:
        return False

    # Prefer create_sim_info if present; otherwise hook a common helper name.
    target = None
    name = None
    for candidate in ("create_sim_info", "_create_and_finalize_sim_info", "create_offspring_sim_info"):
        if hasattr(PregnancyTracker, candidate):
            target = PregnancyTracker
            name = candidate
            break
    if target is None:
        return False

    original = getattr(target, name)

    @Override(original, role=Role.HOST)
    def _create_sim_info_host(orig, self, *args, **kwargs):
        if not SESSION.enabled or not SESSION.is_host or _applying:
            return orig(self, *args, **kwargs)
        result = orig(self, *args, **kwargs)
        try:
            sim_info = result
            if sim_info is None and args:
                sim_info = args[0]
            raw = b""
            if sim_info is not None:
                # Prefer pack/save helpers when available.
                if hasattr(sim_info, "save_sim_info"):
                    try:
                        from protocolbuffers.FileSerialization_pb2 import SimData

                        data = SimData()
                        sim_info.save_sim_info(data)
                        raw = data.SerializeToString()
                    except Exception:
                        raw = b""
                if not raw and hasattr(sim_info, "id"):
                    # Minimal fallback: empty payload still signals a create.
                    raw = b""
            if raw:
                _broadcast(
                    KIND_CREATE_SIM_INFO,
                    {
                        "sim_info": raw,
                        "player_id": int(SESSION.player_id or 0),
                    },
                )
        except Exception:
            pass
        return result

    return True


@MessageHandler(KIND_CREATE_SIM_INFO)
def _joiner_create_sim_info(wrapper):
    global _applying
    if not SESSION.enabled or SESSION.is_host:
        return
    body = wrapper.body or {}
    raw = body.get("sim_info") or b""
    if not raw:
        return
    try:
        import services
        from protocolbuffers.FileSerialization_pb2 import SimData
        from sims.sim_info import SimInfo

        data = SimData()
        data.ParseFromString(raw)
        client = services.client_manager().get_first_client()
        if client is None:
            return
        info = SimInfo(sim_id=data.sim_id, account=client.account)
        info.load_sim_info(data)
        _applying = True
        try:
            client.add_selectable_sim_info(info)
        finally:
            _applying = False
    except Exception:
        _applying = False
