"""Client-side view of the multiplayer session.

Tracks only what the client is told by the server (WELCOME, ROOM_STATE,
PLAYER_JOINED/LEFT, PONG, PRESENCE). Kept deliberately small: the server is
authoritative, the client only mirrors it.
"""

import time

from simmp.constants import DEFAULT_ROOM_ID, PROTOCOL_VERSION
from simmp_client.state.interactions import InteractionMirror
from simmp_client.state.world import WorldMirror


class LocalSession:
    def __init__(self):
        self.connected = False
        self.host = None
        self.port = None
        self.client_id = None
        self.protocol_version = PROTOCOL_VERSION
        self.player_id = None
        self.room_id = DEFAULT_ROOM_ID
        self.server_time = None
        self.server_offset = None
        self.connect_time = None
        self.room_players = {}
        self.presence = {}
        self._presence_seen = {}
        self.presence_ttl = 30.0
        self.last_ping_client_time = None
        self.last_pong_server_time = None
        self.travel_state = "idle"
        self.travel_request_id = None
        self.travel_zone_id = None
        self.travel_requester_id = None
        self.travel_requester_name = None
        self.clock_sync = {}
        self.world = WorldMirror()
        self.interactions = InteractionMirror()

    def apply_welcome(self, payload):
        self.connected = True
        self.player_id = payload["player_id"]
        self.room_id = payload["room_id"]
        self.server_time = payload["server_time"]
        self.server_offset = payload["server_time"] - time.time()
        self.connect_time = time.time()

    def apply_room_state(self, payload):
        self.room_id = payload["room_id"]
        if self.world.room_id != payload["room_id"]:
            self.world.reset(payload["room_id"])
            self.interactions.reset(payload["room_id"])
        self.room_players = {p["player_id"]: p for p in payload["players"]}
        self.presence = {}
        self._presence_seen = {}

    def apply_interaction_state(self, payload):
        self.interactions.apply_full(payload["room_id"], payload["interactions"])

    def apply_interaction_start(self, payload):
        args = payload.get("args")
        self.interactions.apply_start(
            payload["room_id"],
            payload["object_key"],
            payload["player_id"],
            payload["interaction"],
            payload["started_at"],
            args,
            payload.get("affordance"),
            payload.get("affordance_id"),
            payload.get("target"),
        )

    def apply_interaction_free(self, payload):
        self.interactions.apply_free(payload["room_id"], payload["object_key"], payload["cooldown_until"])

    def apply_world_state(self, payload):
        self.world.apply_full(payload["room_id"], payload["objects"])

    def apply_world_delta(self, payload):
        self.world.apply_delta(payload["room_id"], payload["seq"], payload["updates"])

    def apply_object_ownership(self, payload):
        self.world.apply_ownership(payload["key"], payload.get("owner"))

    def apply_object_claim_ack(self, payload):
        self.world.apply_claim_ack(payload["key"], payload.get("owner"))

    def apply_player_joined(self, payload):
        self.room_id = payload["room_id"]
        self.room_players[payload["player_id"]] = {
            "player_id": payload["player_id"],
            "name": payload["name"],
            "connected": True,
        }

    def apply_player_left(self, payload):
        self.room_id = payload["room_id"]
        self.room_players.pop(payload["player_id"], None)
        self.presence.pop(payload["player_id"], None)
        self._presence_seen.pop(payload["player_id"], None)

    def apply_presence(self, payload):
        player_id = payload["player_id"]
        self.presence[player_id] = {
            "player_id": player_id,
            "room_id": payload["room_id"],
            "zone_id": payload["zone_id"],
            "lot_id": payload["lot_id"],
            "timestamp": payload["timestamp"],
        }
        self._presence_seen[player_id] = time.time()

    def purge_stale_presence(self):
        if not self.presence_ttl:
            return
        now = time.time()
        for player_id in list(self.presence.keys()):
            seen = self._presence_seen.get(player_id, now)
            if now - seen > self.presence_ttl:
                self.presence.pop(player_id, None)
                self._presence_seen.pop(player_id, None)

    def apply_pong(self, payload):
        self.last_pong_server_time = payload["server_time"]
        self.server_time = payload["server_time"]
        self.server_offset = payload["server_time"] - time.time()

    def apply_travel_invite(self, payload, request_id):
        self.travel_state = "invited"
        self.travel_request_id = request_id
        self.travel_zone_id = payload["zone_id"]
        self.travel_requester_id = payload["requester_id"]
        self.travel_requester_name = payload["requester_name"]

    def apply_travel_begin(self, payload, request_id):
        self.travel_state = "traveling"
        self.travel_request_id = request_id
        self.travel_zone_id = payload["zone_id"]

    def apply_travel_complete(self, payload, request_id):
        self.travel_state = "idle"
        self.travel_request_id = None
        self.travel_zone_id = None
        self.travel_requester_id = None
        self.travel_requester_name = None

    def apply_travel_abort(self, payload, request_id):
        self.travel_state = "idle"
        self.travel_request_id = None
        self.travel_zone_id = None
        self.travel_requester_id = None
        self.travel_requester_name = None

    def apply_clock_sync(self, payload):
        self.clock_sync.update(
            {
                "player_id": payload.get("player_id"),
                "zone_id": payload["zone_id"],
                "absolute_ticks": payload["absolute_ticks"],
                "real_time": payload["real_time"],
                "clock_speed": payload["clock_speed"],
            }
        )