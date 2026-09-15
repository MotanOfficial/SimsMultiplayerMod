import unittest

from simmp_client.notifications import ToastFilter, player_name, shorten_key


class ToastFilterTests(unittest.TestCase):
    """Pure offline tests for the in-game toast decision logic.

    The game-side rendering (cheat_commands -> ui.py) is wired but not
    exercisable here; these lock the mapping from client log lines to toast
    texts, which is the behavior a live player actually sees.
    """

    def make_world(self, owner_map):
        from simmp_client.state.world import WorldMirror

        world = WorldMirror()
        world.apply_full(
            "lobby",
            100,
            [{"key": key, "owner": owner, "fields": {"x": 0.0, "y": 0.0, "z": 0.0}}
             for key, owner in owner_map.items()],
        )
        return world

    def test_error_lines_toast_verbatim(self):
        f = ToastFilter()
        self.assertEqual(f.pick("[MP][ERROR] connection lost"), "[MP][ERROR] connection lost")

    def test_connect_and_disconnect(self):
        f = ToastFilter()
        self.assertEqual(f.pick("[MP][NET] Connected to 127.0.0.1:8765"), "[MP] Connected to the server")
        self.assertEqual(f.pick("[MP][NET] Disconnected"), "[MP] Disconnected from the server")

    def test_reconnect_toast(self):
        f = ToastFilter()
        self.assertEqual(
            f.pick("[MP][NET] Reconnecting (ownership will be restored on resume)"),
            "[MP] Connection lost; reconnecting...",
        )

    def test_player_join_leave_toast(self):
        f = ToastFilter(cooldown=0)
        self.assertEqual(f.pick("[MP][ROOM] Player 1001 (Alice) joined lobby"), "[MP][ROOM] Player 1001 (Alice) joined lobby")
        self.assertEqual(f.pick("[MP][ROOM] Player 1001 left lobby (disconnect)"), "[MP][ROOM] Player 1001 left lobby (disconnect)")

    def test_room_toast_cooldown_suppresses_burst(self):
        f = ToastFilter(cooldown=60.0)
        self.assertIsNotNone(f.pick("[MP][ROOM] Player 1001 (Alice) joined lobby"))
        self.assertIsNone(f.pick("[MP][ROOM] Player 1002 (Bob) joined lobby"))

    def test_save_messages_toast(self):
        f = ToastFilter()
        self.assertEqual(f.pick("[MP][SAVE] received slot -> save 3"), "[MP][SAVE] received slot -> save 3")
        self.assertEqual(f.pick("[MP][SAVE] SAVE_ACK slot ok=True reached=1"), "[MP][SAVE] SAVE_ACK slot ok=True reached=1")

    def test_travel_invite_toast(self):
        f = ToastFilter()
        text = f.pick("[MP][TRAVEL] Travel invite to zone 4242 from player 1001 (Alice)")
        self.assertEqual(text, "[MP] Travel invite to zone 4242")

    def test_travel_begin_and_complete(self):
        f = ToastFilter(cooldown=0)
        self.assertEqual(f.pick("[MP][TRAVEL] Travel BEGIN to zone 4242"), "[MP] Traveling to zone 4242")
        self.assertEqual(f.pick("[MP][TRAVEL] Travel COMPLETE for zone 4242"), "[MP] Arrived in zone 4242")

    def test_travel_abort_toast(self):
        f = ToastFilter()
        self.assertEqual(f.pick("[MP][TRAVEL] Travel ABORTED: ready timeout"), "[MP] ready timeout")

    def test_own_interaction_start_is_silent(self):
        f = ToastFilter(cooldown=0)
        world = self.make_world({"sim:1234567890": 1000})
        text = f.pick(
            "[MP][SYNC] Interaction start: Read on 'sim:1234567890' by 1000",
            self_player_id=1000,
            world=world,
        )
        self.assertIsNone(text, "own interactions must not toast")

    def test_remote_interaction_on_own_sim_toasts_with_name(self):
        f = ToastFilter(cooldown=0)
        world = self.make_world({"sim:1234567890": 1000})
        roster = {1001: {"player_id": 1001, "name": "Alice", "connected": True}}
        text = f.pick(
            "[MP][SYNC] Interaction start: Read on 'sim:1234567890' by 1001",
            self_player_id=1000,
            roster=roster,
            world=world,
        )
        self.assertEqual(text, "[MP] Alice is Read on sim:567890")

    def test_remote_interaction_on_remote_sim_is_silent(self):
        f = ToastFilter(cooldown=0)
        world = self.make_world({"sim:1234567890": 1001})
        text = f.pick(
            "[MP][SYNC] Interaction start: Read on 'sim:1234567890' by 1001",
            self_player_id=1000,
            world=world,
        )
        self.assertIsNone(text, "interactions on sims the other player owns stay console-only")

    def test_remote_ownership_toasts_with_name(self):
        f = ToastFilter(cooldown=0)
        roster = {1001: {"player_id": 1001, "name": "Alice", "connected": True}}
        text = f.pick(
            "[MP][SYNC] Object 'sim:1234567890' owner -> 1001",
            self_player_id=1000,
            roster=roster,
        )
        self.assertEqual(text, "[MP] Alice took over sim:567890")

    def test_own_ownership_is_silent(self):
        f = ToastFilter(cooldown=0)
        text = f.pick(
            "[MP][SYNC] Object 'sim:1234567890' owner -> 1000",
            self_player_id=1000,
        )
        self.assertIsNone(text)

    def test_release_ownership_is_silent(self):
        f = ToastFilter(cooldown=0)
        roster = {1001: {"player_id": 1001, "name": "Alice", "connected": True}}
        text = f.pick(
            "[MP][SYNC] Object 'sim:1234567890' owner -> None",
            self_player_id=1000,
            roster=roster,
        )
        self.assertIsNone(text, "a release must not toast")

    def test_ownership_cooldown_suppresses_burst(self):
        f = ToastFilter(cooldown=60.0)
        text = f.pick("[MP][SYNC] Object 'sim:1' owner -> 1001", self_player_id=1000)
        self.assertIsNotNone(text)
        self.assertIsNone(f.pick("[MP][SYNC] Object 'sim:2' owner -> 1001", self_player_id=1000))

    def test_unknown_lines_are_silent(self):
        f = ToastFilter()
        self.assertIsNone(f.pick("[MP][SYNC] World delta from=1000 seq=3 keys=['sim:1']"))
        self.assertIsNone(f.pick("[MP][NET] Pong server_time=1.0"))

    def test_shorten_key(self):
        self.assertEqual(shorten_key("sim:9876543210"), "sim:543210")
        self.assertEqual(shorten_key("sofa"), "sofa")

    def test_player_name_fallbacks(self):
        roster = {1001: {"player_id": 1001, "name": "Alice", "connected": True}}
        self.assertEqual(player_name(roster, 1001), "Alice")
        self.assertEqual(player_name(roster, 9999), "Player 9999")
        self.assertEqual(player_name(None, 9999), "Player 9999")


if __name__ == "__main__":
    unittest.main()