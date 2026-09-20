import unittest

from simmp_client.state.world import WorldMirror, lerp


class LerpTests(unittest.TestCase):
    def test_lerp_bounds(self):
        self.assertEqual(lerp(0, 10, 0.0), 0.0)
        self.assertEqual(lerp(0, 10, 1.0), 10.0)
        self.assertEqual(lerp(0, 10, 0.5), 5.0)


class WorldMirrorTests(unittest.TestCase):
    def _mirror(self, zone_id=None):
        mirror = WorldMirror()
        mirror.apply_full("lobby", zone_id, [])
        return mirror

    def test_apply_full_replaces_catalog(self):
        mirror = self._mirror(100)
        mirror.apply_full(
            "lobby",
            100,
            [
                {"key": "sofa", "owner": 1000, "fields": {"x": 1.0, "y": 2.0, "z": 3.0}},
                {"key": "table", "owner": None, "fields": {}},
            ],
        )
        self.assertEqual(mirror.room_id, "lobby")
        self.assertEqual(mirror.zone_id, 100)
        self.assertEqual(mirror.count(), 2)
        self.assertEqual(mirror.get("sofa").owner, 1000)
        self.assertEqual(mirror.get("table").owner, None)

    def test_apply_full_on_zone_change_replaces(self):
        mirror = self._mirror(100)
        mirror.apply_full("lobby", 100, [{"key": "sofa", "owner": 1000, "fields": {"x": 1.0}}])
        mirror.apply_full("lobby", 200, [{"key": "stove", "owner": None, "fields": {}}])
        self.assertEqual(mirror.zone_id, 200)
        self.assertEqual(mirror.count(), 1)
        self.assertIn("stove", mirror.objects)
        self.assertNotIn("sofa", mirror.objects)

    def test_apply_state_part_reconstructs_chunked_snapshot(self):
        mirror = self._mirror(100)
        mirror.apply_state_part("lobby", 100, [{"key": "a", "owner": 1, "fields": {"x": 1.0}}], part=0, total=3)
        mirror.apply_state_part("lobby", 100, [{"key": "b", "owner": 2, "fields": {}}], part=1, total=3)
        mirror.apply_state_part("lobby", 100, [{"key": "c", "owner": None, "fields": {}}], part=2, total=3)
        self.assertEqual(sorted(mirror.objects), ["a", "b", "c"])
        self.assertEqual(mirror.get("b").owner, 2)

    def test_apply_state_part_ignores_late_part_for_other_zone(self):
        mirror = self._mirror(100)
        mirror.apply_state_part("lobby", 100, [{"key": "a", "owner": 1, "fields": {}}], part=0, total=2)
        mirror.apply_state_part("lobby", 200, [{"key": "b", "owner": 1, "fields": {}}], part=1, total=2)
        self.assertEqual(sorted(mirror.objects), ["a"])

    def test_apply_delta_merges_fields(self):
        mirror = self._mirror(100)
        mirror.apply_full("lobby", 100, [{"key": "sofa", "owner": 1000, "fields": {"x": 1.0}}])
        mirror.apply_delta("lobby", 100, 1, [{"key": "sofa", "fields": {"y": 5.0, "z": 0.0}}])
        self.assertEqual(mirror.last_seq, 1)
        self.assertEqual(mirror.get("sofa").fields, {"x": 1.0, "y": 5.0, "z": 0.0})

    def test_apply_delta_stale_seq_ignored(self):
        mirror = self._mirror(100)
        mirror.apply_full("lobby", 100, [{"key": "sofa", "owner": 1000, "fields": {"x": 1.0}}])
        mirror.apply_delta("lobby", 100, 5, [{"key": "sofa", "fields": {"y": 1.0}}])
        mirror.apply_delta("lobby", 100, 4, [{"key": "sofa", "fields": {"y": 99.0}}])
        self.assertEqual(mirror.last_seq, 5)
        self.assertEqual(mirror.get("sofa").fields["y"], 1.0)

    def test_apply_delta_wrong_room_ignored(self):
        mirror = self._mirror(100)
        mirror.apply_full("lobby", 100, [{"key": "sofa", "owner": None, "fields": {}}])
        mirror.apply_delta("alpha", 100, 1, [{"key": "sofa", "fields": {"x": 1.0}}])
        self.assertNotEqual(mirror.get("sofa").fields.get("x"), 1.0)

    def test_apply_delta_wrong_zone_ignored(self):
        mirror = self._mirror(100)
        mirror.apply_full("lobby", 100, [{"key": "sofa", "owner": None, "fields": {}}])
        mirror.apply_delta("lobby", 200, 1, [{"key": "sofa", "fields": {"x": 9.0}}])
        self.assertNotEqual(mirror.get("sofa").fields.get("x"), 9.0)

    def test_apply_delta_creates_unknown_key(self):
        mirror = self._mirror(100)
        mirror.apply_delta("lobby", 100, 1, [{"key": "sofa", "fields": {"x": 2.0}}])
        self.assertIn("sofa", mirror.objects)

    def test_apply_ownership_updates_owner(self):
        mirror = self._mirror(100)
        mirror.apply_full("lobby", 100, [{"key": "sofa", "owner": None, "fields": {}}])
        mirror.apply_ownership("sofa", 1000, zone_id=100)
        self.assertEqual(mirror.get("sofa").owner, 1000)
        mirror.apply_claim_ack("sofa", None)
        self.assertIsNone(mirror.get("sofa").owner)

    def test_exclusive_ownership_single_owner(self):
        mirror = self._mirror(100)
        mirror.apply_full("lobby", 100, [{"key": "sim:1", "owner": 1000, "fields": {}}])
        sim = mirror.get("sim:1")
        self.assertTrue(sim.is_owned_by(1000))
        self.assertFalse(sim.is_owned_by(1001))
        self.assertTrue(sim.exclusively_owned_by(1000))
        mirror.apply_ownership("sim:1", 1001, zone_id=100)
        self.assertTrue(mirror.get("sim:1").is_owned_by(1001))
        self.assertFalse(mirror.get("sim:1").is_owned_by(1000))
        mirror.apply_claim_ack("sim:1", None)
        self.assertIsNone(mirror.get("sim:1").owner)

    def test_apply_ownership_wrong_zone_ignored(self):
        mirror = self._mirror(100)
        mirror.apply_full("lobby", 100, [{"key": "sofa", "owner": None, "fields": {}}])
        mirror.apply_ownership("sofa", 1000, zone_id=200)
        self.assertIsNone(mirror.get("sofa").owner)

    def test_position_and_display_position_smoothing(self):
        mirror = self._mirror(100)
        mirror.apply_full("lobby", 100, [{"key": "sofa", "owner": None, "fields": {"x": 0.0, "y": 0.0, "z": 0.0}}])
        sofa = mirror.get("sofa")
        # No anchor yet -> exact.
        self.assertEqual(mirror.get("sofa").display_position(now=100.0), (0.0, 0.0, 0.0))

        # A move anchors the old position and eases toward the target.
        sofa.merge_fields({"x": 10.0, "y": 0.0, "z": 0.0}, now=100.0)
        self.assertEqual(sofa.display_position(now=100.0), (0.0, 0.0, 0.0))
        self.assertEqual(sofa.display_position(now=100.25, rate=2.0), (5.0, 0.0, 0.0))
        self.assertEqual(sofa.display_position(now=101.0, rate=2.0), (10.0, 0.0, 0.0))

    def test_position_missing_fields_returns_none(self):
        mirror = self._mirror(100)
        mirror.apply_full("lobby", 100, [{"key": "table", "owner": None, "fields": {"state": "clean"}}])
        self.assertIsNone(mirror.get("table").position())


if __name__ == "__main__":
    unittest.main()