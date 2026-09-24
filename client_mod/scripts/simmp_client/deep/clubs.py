"""Club create/update/remove, membership, and gathering deep relays.

Opaque ``club_data`` strings are EA Clubs_pb2.Club text-format payloads from
the joiner UI; the host merges them and mutates ClubService.
"""

from __future__ import division

from simmp.deep import (
    KIND_ADD_SIM_TO_CLUB,
    KIND_CREATE_CLUB,
    KIND_END_CLUB_GATHERING,
    KIND_REMOVE_CLUB,
    KIND_REQUEST_CLUB_INVITE,
    KIND_START_CLUB_GATHERING,
    KIND_UPDATE_CLUB,
    WrapperMessage,
)
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


def _sim_id_from_arg(value):
    if value is None:
        return 0
    try:
        return int(getattr(value, "id", value))
    except Exception:
        return 0


def _player_sim_info(player_id):
    try:
        from simmp_client.deep import sim_select
        import services

        sim_id = sim_select.get_active_sim_id_for_player(player_id)
        if not sim_id:
            return None
        return services.sim_info_manager().get(sim_id)
    except Exception:
        return None


def _club_service():
    try:
        import services

        return services.get_club_service()
    except Exception:
        return None


def install_club_hooks():
    try:
        from clubs import club_commands
    except Exception:
        try:
            import club_commands
        except Exception:
            return False

    ok = False

    create_fn = getattr(club_commands, "create_club", None)
    if create_fn is not None:

        @Override(create_fn, role=Role.JOINER)
        def _create_club_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                club_data = args[0] if args else kwargs.get("club_data")
                club_data_s = str(club_data) if club_data is not None else ""
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_CREATE_CLUB,
                {
                    "club_data": club_data_s,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    update_fn = getattr(club_commands, "update_club", None)
    if update_fn is not None:

        @Override(update_fn, role=Role.JOINER)
        def _update_club_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                club_data = args[0] if args else kwargs.get("club_data")
                club_data_s = str(club_data) if club_data is not None else ""
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_UPDATE_CLUB,
                {
                    "club_data": club_data_s,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    remove_fn = getattr(club_commands, "remove_club_by_id", None)
    if remove_fn is not None:

        @Override(remove_fn, role=Role.JOINER)
        def _remove_club_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                club_id = int(args[0]) if args else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_REMOVE_CLUB,
                {
                    "club_id": club_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    add_fn = getattr(club_commands, "add_sim_to_club_by_id", None)
    if add_fn is not None:

        @Override(add_fn, role=Role.JOINER)
        def _add_sim_to_club_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                sim_id = _sim_id_from_arg(args[0] if args else None)
                club_id = int(args[1]) if len(args) > 1 else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_ADD_SIM_TO_CLUB,
                {
                    "sim_id": sim_id,
                    "club_id": club_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    start_fn = getattr(club_commands, "start_gathering_by_club_id", None)
    if start_fn is not None:

        @Override(start_fn, role=Role.JOINER)
        def _start_gathering_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                club_id = int(args[0]) if args else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_START_CLUB_GATHERING,
                {
                    "club_id": club_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    end_fn = getattr(club_commands, "end_gathering_by_club_id", None)
    if end_fn is not None:

        @Override(end_fn, role=Role.JOINER)
        def _end_gathering_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                club_id = int(args[0]) if args else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_END_CLUB_GATHERING,
                {
                    "club_id": club_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    invite_fn = getattr(club_commands, "request_club_invite", None)
    if invite_fn is None:
        invite_fn = getattr(club_commands, "request_invite", None)
    if invite_fn is not None:

        @Override(invite_fn, role=Role.JOINER)
        def _request_club_invite_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                club_id = int(args[0]) if args else 0
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_REQUEST_CLUB_INVITE,
                {
                    "club_id": club_id,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


def _parse_club_pb(club_data_s):
    try:
        from google.protobuf import text_format
        from protocolbuffers import Clubs_pb2

        club = Clubs_pb2.Club()
        text_format.Merge(club_data_s or "", club)
        return club
    except Exception:
        return None


@MessageHandler(KIND_CREATE_CLUB)
def _host_create_club(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    club_pb = _parse_club_pb(body.get("club_data") or "")
    if club_pb is None:
        return
    svc = _club_service()
    if svc is None:
        return
    player_id = int(body.get("player_id") or 0)
    try:
        club = svc.create_club(club_data=club_pb, from_load=False)
        sim_info = _player_sim_info(player_id)
        if club is not None and sim_info is not None:
            try:
                from clubs.club_tuning import ClubTunables

                club.show_club_notification(sim_info, ClubTunables.CLUB_NOTIFICATION_CREATE)
            except Exception:
                pass
    except Exception:
        return


@MessageHandler(KIND_UPDATE_CLUB)
def _host_update_club(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    club_pb = _parse_club_pb(body.get("club_data") or "")
    if club_pb is None:
        return
    svc = _club_service()
    if svc is None:
        return
    try:
        svc.update_club_from_data(club_pb)
    except Exception:
        return


@MessageHandler(KIND_REMOVE_CLUB)
def _host_remove_club(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    club_id = int(body.get("club_id") or 0)
    if not club_id:
        return
    svc = _club_service()
    if svc is None:
        return
    try:
        club = svc.get_club_by_id(club_id)
        if club is None:
            return
        svc.remove_club(club)
    except Exception:
        return


@MessageHandler(KIND_ADD_SIM_TO_CLUB)
def _host_add_sim_to_club(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    sim_id = int(body.get("sim_id") or 0)
    club_id = int(body.get("club_id") or 0)
    if not sim_id or not club_id:
        return
    try:
        import services

        svc = _club_service()
        if svc is None:
            return
        club = svc.get_club_by_id(club_id)
        if club is None:
            return
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        club.add_member(sim_info)
    except Exception:
        return


@MessageHandler(KIND_START_CLUB_GATHERING)
def _host_start_club_gathering(wrapper):
    """Start a gathering on the current zone when valid; otherwise no-op.

    Full hangout-location dialog flow is UI-heavy; host starts on-current-lot
    when the club allows it. Dialog responses continue via P6.
    """
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    club_id = int(body.get("club_id") or 0)
    player_id = int(body.get("player_id") or 0)
    if not club_id:
        return
    try:
        import services

        svc = _club_service()
        if svc is None:
            return
        club = svc.get_club_by_id(club_id)
        if club is None:
            return
        sim_info = _player_sim_info(player_id)
        if sim_info is None:
            return
        zone_id = services.current_zone_id()
        try:
            if not club.is_zone_valid_for_gathering(zone_id):
                return
        except Exception:
            pass
        invited = (sim_info,)
        try:
            svc.start_gathering(club, invited_sims=invited)
        except TypeError:
            try:
                svc.start_gathering(club, invited)
            except Exception:
                return
    except Exception:
        return


@MessageHandler(KIND_END_CLUB_GATHERING)
def _host_end_club_gathering(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    club_id = int(body.get("club_id") or 0)
    if not club_id:
        return
    try:
        svc = _club_service()
        if svc is None:
            return
        club = svc.get_club_by_id(club_id)
        if club is None:
            return
        gathering = svc.clubs_to_gatherings_map.get(club)
        if gathering is None:
            return
        gathering._self_destruct()
    except Exception:
        return


@MessageHandler(KIND_REQUEST_CLUB_INVITE)
def _host_request_club_invite(wrapper):
    """Best-effort invite request: prefer replaying the original club command."""
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    club_id = int(body.get("club_id") or 0)
    if not club_id:
        return
    try:
        from clubs import club_commands

        fn = getattr(club_commands, "request_club_invite", None) or getattr(
            club_commands, "request_invite", None
        )
        if fn is not None:
            fn(club_id)
            return
    except Exception:
        pass
    # Fallback: start gathering with requesting sim if club has hangout.
    try:
        svc = _club_service()
        if svc is None:
            return
        club = svc.get_club_by_id(club_id)
        if club is None:
            return
        sim_info = _player_sim_info(int(body.get("player_id") or 0))
        if sim_info is None:
            return
        try:
            club.show_club_gathering_dialog(sim_info)
        except Exception:
            svc.start_gathering(club, invited_sims=(sim_info,))
    except Exception:
        return