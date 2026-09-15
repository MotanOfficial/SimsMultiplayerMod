import unittest

from simmp_client.state.interactions import InteractionMirror


class InteractionMirrorTests(unittest.TestCase):
    def _mirror(self, zone_id=None):
        mirror = InteractionMirror()
        mirror.apply_full("lobby", zone_id, [])
        return mirror

    def test_apply_full_replaces(self):
        mirror = self._mirror(100)
        mirror.apply_full(
            "lobby",
            100,
            [{"object_key": "sofa", "player_id": 1000, "interaction": "Read", "started_at": 1.0}],
        )
        self.assertEqual(mirror.room_id, "lobby")
        self.assertEqual(mirror.zone_id, 100)
        self.assertEqual(mirror.count(), 1)
        self.assertEqual(mirror.get("sofa")["player_id"], 1000)

    def test_apply_start_sets_and_clears_cooldown(self):
        mirror = self._mirror(100)
        mirror.apply_free("lobby", 100, "sofa", 500.0)
        self.assertEqual(mirror.cooldown_until("sofa"), 500.0)
        mirror.apply_start(
            "lobby",
            100,
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

    def test_apply_start_wrong_zone_ignored(self):
        mirror = self._mirror(100)
        mirror.apply_start("lobby", 200, "sofa", 1000, "Read", 1.0)
        self.assertEqual(mirror.count(), 0)

    def test_apply_full_stores_hints_and_defaults_absent(self):
        mirror = self._mirror(100)
        mirror.apply_full(
            "lobby",
            100,
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
        mirror = self._mirror(100)
        mirror.apply_full("lobby", 100, [{"object_key": "sofa", "player_id": 1000, "interaction": "Read", "started_at": 1.0}])
        mirror.apply_free("lobby", 100, "sofa", 500.0)
        self.assertEqual(mirror.count(), 0)
        self.assertEqual(mirror.cooldown_until("sofa"), 500.0)

    def test_wrong_room_ignored(self):
        mirror = self._mirror(100)
        mirror.apply_start("alpha", 100, "sofa", 1000, "Read", 1.0)
        self.assertEqual(mirror.count(), 0)
        mirror.apply_free("alpha", 100, "sofa", 1.0)
        self.assertEqual(mirror.cooldown_until("sofa"), 0)


if __name__ == "__main__":
    unittest.main()