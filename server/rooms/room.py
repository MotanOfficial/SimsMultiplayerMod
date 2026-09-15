"""Thin room conveniences used by the server.

Sessions hold the authoritative player/room state (server/state/session.py).
This module offers lookup helpers that the connection handler layer uses so
the networking code never touches player internals directly.
"""


class RoomManager:
    def __init__(self, session):
        self._session = session

    def get_room(self, room_id):
        return self._session.get_room(room_id)

    def get_or_create_room(self, room_id):
        return self._session.get_or_create_room(room_id)

    def move_player(self, player, room_id):
        return self._session.move_player(player, room_id)