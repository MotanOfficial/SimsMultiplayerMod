import unittest

from simmp_client.state.interactions import InteractionMirror


class InteractionMirrorTests(unittest.TestCase):
    def test_apply_full_replaces(self):
        mirror = InteractionMirror()
        mirror.apply_full(
            "lobby",
            [{"object_key": "sofa", "player_id": 1000, "interaction": "Read", "started_at": 1.0}],
        )
        self.assertEqual(mirror.room_id, "lobby")
        self.assertEqual(mirror.count(), 1)
        self.assertEqual(mirror.get("sofa")["player_id"], 1000)

    def test_apply_start_sets_and_clears_cooldown(self):
        mirror = InteractionMirror()
        mirror.apply_full("lobby", [])
        mirror.apply_free("lobby", "sofa", 500.0)
        self.assertEqual(mirror.cooldown_until("sofa"), 500.0)
        mirror.apply_start(
            "lobby",
            "sofa",
            1000,
            "Read",
            1.0,
            affordance="Read",
            affordance_id=9001,
            target="sim:7",
        )
        self.assertEqual(mirror.count(), 1)
        self.assertEqual(mirror.get("sofa")["interaction"], "Read")
        self.assertEqual(mirror.get("sofa")["affordance"], "Read")
        self.assertEqual(mirror.get("sofa")["affordance_id"], 9001)
        self.assertEqual(mirror.get("sofa")["target"], "sim:7")
        self.assertEqual(mirror.cooldown_until("sofa"), 0)

    def test_apply_full_stores_hints_and_defaults_absent(self):
        mirror = InteractionMirror()
        mirror.apply_full(
            "lobby",
            [
                {
                    "object_key": "sim:42",
                    "player_id": 1000,
                    "interaction": "Read",
                    "started_at": 1.0,
                    "affordance": "Read",
                    "affordance_id": 9001,
                    "target": "sim:7",
                },
                {"object_key": "sofa", "player_id": 1001, "interaction": "Sit", "started_at": 2.0},
            ],
        )
        self.assertEqual(mirror.get("sim:42")["affordance_id"], 9001)
        self.assertEqual(mirror.get("sim:42")["target"], "sim:7")
        self.assertEqual(mirror.get("sofa")["affordance"], None)
        self.assertEqual(mirror.get("sofa")["affordance_id"], None)

    def test_apply_free_removes(self):
        mirror = InteractionMirror()
        mirror.apply_full("lobby", [{"object_key": "sofa", "player_id": 1000, "interaction": "Read", "started_at": 1.0}])
        mirror.apply_free("lobby", "sofa", 500.0)
        self.assertEqual(mirror.count(), 0)
        self.assertEqual(mirror.cooldown_until("sofa"), 500.0)

    def test_wrong_room_ignored(self):
        mirror = InteractionMirror()
        mirror.apply_full("lobby", [])
        mirror.apply_start("alpha", "sofa", 1000, "Read", 1.0)
        self.assertEqual(mirror.count(), 0)
        mirror.apply_free("alpha", "sofa", 1.0)
        self.assertEqual(mirror.cooldown_until("sofa"), 0)


if __name__ == "__main__":
    unittest.main()