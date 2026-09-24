"""Social media (Simstagram) friend / reaction / seen relays."""

from __future__ import division

from simmp.deep import (
    KIND_SOCIAL_MEDIA_ADD_REACTION,
    KIND_SOCIAL_MEDIA_MARK_MESSAGES_SEEN,
    KIND_SOCIAL_MEDIA_MARK_POSTS_SEEN,
    KIND_SOCIAL_MEDIA_REMOVE_FRIEND,
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


def _as_int(value, default=0):
    if value is None:
        return default
    try:
        return int(getattr(value, "id", getattr(value, "value", value)))
    except Exception:
        return default


def install_social_media_hooks():
    try:
        from social_media import social_media_commands
    except Exception:
        return False

    ok = False

    rem_fn = getattr(social_media_commands, "social_media_remove_friend", None)
    if rem_fn is not None:

        @Override(rem_fn, role=Role.JOINER)
        def _remove_friend_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                author = _as_int(args[0] if args else kwargs.get("author_sim"))
                target = _as_int(args[1] if len(args) > 1 else kwargs.get("target_sim"))
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SOCIAL_MEDIA_REMOVE_FRIEND,
                {
                    "author_sim": author,
                    "target_sim": target,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    react_fn = getattr(social_media_commands, "add_social_media_reaction_to_post_ids", None)
    if react_fn is not None:

        @Override(react_fn, role=Role.JOINER)
        def _add_reaction_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                author = _as_int(args[0] if args else kwargs.get("author_sim"))
                target = _as_int(args[1] if len(args) > 1 else kwargs.get("target_sim"))
                post_id = _as_int(args[2] if len(args) > 2 else kwargs.get("post_id"))
                post_type = _as_int(args[3] if len(args) > 3 else kwargs.get("post_type"))
                narrative = _as_int(args[4] if len(args) > 4 else kwargs.get("narrative"))
                polarity = _as_int(args[5] if len(args) > 5 else kwargs.get("polarity"))
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SOCIAL_MEDIA_ADD_REACTION,
                {
                    "author_sim": author,
                    "target_sim": target,
                    "post_id": post_id,
                    "post_type": post_type,
                    "narrative": narrative,
                    "polarity": polarity,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    posts_fn = getattr(social_media_commands, "social_media_mark_posts_seen", None)
    if posts_fn is not None:

        @Override(posts_fn, role=Role.JOINER)
        def _mark_posts_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                author = _as_int(args[0] if args else kwargs.get("author_sim"))
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SOCIAL_MEDIA_MARK_POSTS_SEEN,
                {
                    "author_sim": author,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    msgs_fn = getattr(social_media_commands, "social_media_mark_messages_seen", None)
    if msgs_fn is not None:

        @Override(msgs_fn, role=Role.JOINER)
        def _mark_msgs_joiner(original, *args, **kwargs):
            if not SESSION.enabled or SESSION.is_host:
                return original(*args, **kwargs)
            try:
                author = _as_int(args[0] if args else kwargs.get("author_sim"))
            except Exception:
                return original(*args, **kwargs)
            _relay_to_host(
                KIND_SOCIAL_MEDIA_MARK_MESSAGES_SEEN,
                {
                    "author_sim": author,
                    "player_id": int(SESSION.player_id or 0),
                },
            )
            return None

        ok = True

    return ok


def _sim_info(sim_id):
    try:
        import services

        return services.sim_info_manager().get(int(sim_id))
    except Exception:
        return None


@MessageHandler(KIND_SOCIAL_MEDIA_REMOVE_FRIEND)
def _host_remove_friend(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from social_media import social_media_commands

        social_media_commands.social_media_remove_friend(
            int(body.get("author_sim") or 0),
            int(body.get("target_sim") or 0),
        )
    except Exception:
        return


@MessageHandler(KIND_SOCIAL_MEDIA_ADD_REACTION)
def _host_add_reaction(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        from social_media import social_media_commands
        from social_media import SocialMediaPolarity, SocialMediaPostType, SocialMediaNarrative
        import services

        post_type = SocialMediaPostType(int(body.get("post_type") or 0)).name
        narrative = SocialMediaNarrative(int(body.get("narrative") or 0)).name
        polarity = SocialMediaPolarity(int(body.get("polarity") or 0)).name
        client = services.get_first_client()
        conn = int(getattr(client, "id", 0) or 0) if client else 0
        social_media_commands.add_social_media_reaction_to_post(
            int(body.get("author_sim") or 0),
            int(body.get("target_sim") or 0),
            int(body.get("post_id") or 0),
            post_type,
            narrative,
            polarity,
            conn,
        )
    except Exception:
        try:
            from social_media import social_media_commands

            social_media_commands.add_social_media_reaction_to_post_ids(
                int(body.get("author_sim") or 0),
                int(body.get("target_sim") or 0),
                int(body.get("post_id") or 0),
                int(body.get("post_type") or 0),
                int(body.get("narrative") or 0),
                int(body.get("polarity") or 0),
            )
        except Exception:
            return


@MessageHandler(KIND_SOCIAL_MEDIA_MARK_POSTS_SEEN)
def _host_mark_posts_seen(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services

        svc = services.get_social_media_service()
        info = _sim_info(body.get("author_sim"))
        if svc is None or info is None:
            return
        svc.mark_posts_seen(info.sim_id)
    except Exception:
        return


@MessageHandler(KIND_SOCIAL_MEDIA_MARK_MESSAGES_SEEN)
def _host_mark_messages_seen(wrapper):
    if not SESSION.enabled or not SESSION.is_host:
        return
    body = wrapper.body or {}
    try:
        import services

        svc = services.get_social_media_service()
        info = _sim_info(body.get("author_sim"))
        if svc is None or info is None:
            return
        svc.mark_messages_seen(info.sim_id)
    except Exception:
        return
